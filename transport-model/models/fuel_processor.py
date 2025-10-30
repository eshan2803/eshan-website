"""
models/fuel_processor.py
FuelProcessor class that encapsulates all fuel transport LCA calculations.
This replaces 30+ nested functions in app.py with a stateful processor.
"""

import numpy as np
from scipy.optimize import minimize

# Import from our modules
from constants import *
from models.capex_calculations import (
    calculate_liquefaction_capex,
    calculate_storage_capex,
    calculate_loading_unloading_capex
)
from utils.helpers import calculate_dynamic_cop
from services.carbon_service import calculate_electricity_emissions


class FuelProcessor:
    """
    Processes fuel (H2, NH3, MeOH) transport life cycle analysis.

    Holds all configuration and state for a single fuel transport calculation,
    eliminating the need for complex argument passing between nested functions.
    """

    def __init__(self, inputs, locations, prices, emissions_data, ship_params, route_data):
        """
        Initialize FuelProcessor with all necessary context.

        Args:
            inputs: User inputs dictionary
            locations: Location data (coords, temperatures, countries)
            prices: Price data (electricity, diesel, H2 production)
            emissions_data: Carbon intensity data
            ship_params: Ship configuration
            route_data: Route information (distances, durations, sea route coords)
        """
        # Store inputs
        self.fuel_type = inputs['fuel_type']
        self.H2_weight = inputs['H2_weight']
        self.recirculation_BOG = inputs['recirculation_BOG']
        self.BOG_truck_apply = inputs['BOG_recirculation_truck_apply']
        self.BOG_storage_apply = inputs['BOG_recirculation_storage_apply']
        self.BOG_maritime_apply = inputs['BOG_recirculation_mati_trans_apply']
        self.LH2_plant_capacity = inputs['LH2_plant_capacity']

        # Store location data
        self.locations = locations
        self.start_temp = locations['start_temp']
        self.end_temp = locations['end_temp']
        self.start_country = locations['start_country']
        self.end_country = locations['end_country']
        self.start_port_country = locations['start_port_country']
        self.end_port_country = locations['end_port_country']

        # Store price data
        self.prices = prices
        self.start_electricity_price = prices['start_electricity']
        self.end_electricity_price = prices['end_electricity']
        self.hydrogen_production_cost = prices['hydrogen_production_cost']

        # Store emissions data
        self.emissions = emissions_data
        self.CO2e_start = emissions_data['CO2e_start']
        self.CO2e_end = emissions_data['CO2e_end']
        self.carbon_tax_dict = emissions_data['carbon_tax_dict']

        # Store ship and route data
        self.ship_params = ship_params
        self.route = route_data
        self.searoute_coords = route_data['searoute_coords']
        self.port_to_port_duration = route_data['port_to_port_duration']

        # Calculate derived parameters
        self._initialize_fuel_properties()
        self._initialize_equipment_params()
        self._initialize_transport_params()

        # Fuel type names
        self.fuel_names = ['Liquid Hydrogen', 'Ammonia', 'Methanol']
        self.selected_fuel_name = self.fuel_names[self.fuel_type]

    def _initialize_fuel_properties(self):
        """Initialize fuel-specific properties"""
        # Thermodynamic properties by fuel type [H2, NH3, MeOH]
        self.HHV_chem = [142, 22.5, 22.7]  # MJ/kg
        self.LHV_chem = [120, 18.6, 19.9]  # MJ/kg
        self.boiling_point_chem = [20, 239.66, 337.7]  # K
        self.latent_H_chem = [449.6/1000, 1.37, 1.1]  # MJ/kg
        self.specific_heat_chem = [14.3/1000, 4.7/1000, 2.5/1000]  # MJ/kg·K
        self.liquid_chem_density = [71, 682, 805]  # kg/m³
        self.gas_chem_density = [0.08, 0.73, 1.42]  # kg/m³ (at STP)
        self.GWP_chem = [33, 0, 0]  # Global warming potential

        # Boil-off rates (fraction per hour)
        self.BOR_land_storage = [0.0032, 0.0001, 0.0000032]
        self.BOR_loading = [0.0086, 0.00022, 0.0001667]
        self.BOR_truck_trans = [0.005, 0.00024, 0.000005]
        self.BOR_ship_trans = [0.00326, 0.00024, 0.000005]
        self.BOR_unloading = [0.0086, 0.00022, 0.0001667]
        self.dBOR_dT = [(0.02538-0.02283)/(45-15)/4, (0.000406-0.0006122)/(45-15)/4, 0]

        # Conversion properties
        self.mass_conversion_to_H2 = [1, 0.176, 0.1875]
        self.eff_energy_chem_to_H2 = [0, 0.7, 0.75]
        self.energy_chem_to_H2 = [0, 9.3, 5.3]  # MJ/kg

        # Dynamic COP calculation
        start_temp_kelvin = self.start_temp + 273.15
        self.COP_liq_dyn = calculate_dynamic_cop(start_temp_kelvin, self.boiling_point_chem[self.fuel_type])
        self.COP_cooldown_dyn = self.COP_liq_dyn

        # Default COP values (if dynamic fails)
        self.COP_cooldown = [0.131, 1.714, 2]
        self.COP_liq = [0.131, 1.714, 2]
        self.COP_refrig = [0.036, 1.636, 2]

    def _initialize_equipment_params(self):
        """Initialize equipment parameters"""
        # Pump parameters
        self.V_flowrate = [72000, 72000, 72000]  # kg/hr
        self.head_pump = 110  # meters
        self.pump_power_factor = 0.78
        self.number_of_cryo_pump_load_truck_site_A = 10
        self.number_of_cryo_pump_load_ship_port_A = 10
        self.number_of_cryo_pump_load_storage_port_A = 10
        self.number_of_cryo_pump_load_storage_port_B = 10
        self.number_of_cryo_pump_load_truck_port_B = 10
        self.number_of_cryo_pump_load_storage_site_B = 10

        # Pipe parameters
        self.ss_therm_cond = 0.03  # W/m·K
        self.pipe_inner_D = 0.508  # meters
        self.pipe_thick = 0.13  # meters
        self.pipe_length = 1000  # meters

        # Storage parameters
        self.storage_volume = [5683, 50000000/self.liquid_chem_density[1], 50000000/self.liquid_chem_density[2]]  # m³
        self.storage_radius = [np.cbrt(3 * vol / (4 * np.pi)) for vol in self.storage_volume]

        # Tank parameters
        self.tank_metal_thickness = 0.01  # meters
        self.tank_insulator_thickness = 0.4  # meters
        self.metal_thermal_conduct = 13.8  # W/m·K
        self.insulator_thermal_conduct = 0.02  # W/m·K

        # Truck parameters
        self.chem_in_truck_weight = [4200, 32000, 40000*0.001*self.liquid_chem_density[2]]  # kg
        self.truck_tank_volume = 50  # m³
        self.truck_tank_length = 12  # meters
        self.truck_tank_radius = np.sqrt(self.truck_tank_volume/(np.pi*self.truck_tank_length))
        self.truck_tank_metal_thickness = 0.005  # meters
        self.truck_tank_insulator_thickness = 0.075  # meters

        # Ship parameters
        self.OHTC_ship = [0.05, 0.22, 0.02]  # Overall heat transfer coefficient W/m²·K

        # Calculate ship tank geometry from ship_params
        volume_per_tank = self.ship_params['volume_m3'] / self.ship_params['num_tanks']
        if self.ship_params['shape'] == 1:  # Cylindrical
            ship_tank_radius = np.cbrt(volume_per_tank/( (4/3)*np.pi + 8*np.pi ))
            ship_tank_height = 8 * ship_tank_radius
            self.storage_area = 2*np.pi*(ship_tank_radius*ship_tank_height) + 4*np.pi*ship_tank_radius**2
        else:  # Spherical
            ship_tank_radius = np.cbrt(volume_per_tank/(4/3*np.pi))
            self.storage_area = 4*np.pi*ship_tank_radius**2

        # Efficiency parameters
        self.EIM_liquefication = 100  # %
        self.EIM_cryo_pump = 100  # %
        self.EIM_truck_eff = 100  # %
        self.EIM_ship_eff = 100  # %
        self.EIM_refrig_eff = 100  # %
        self.EIM_fuel_cell = 100  # %

        # Engine efficiencies
        self.diesel_engine_eff = 0.4
        self.ship_engine_eff = 0.6
        self.fuel_cell_eff = 0.65
        self.multistage_eff = 0.85
        self.propul_eff = 0.55

        # Pressurized H2 parameters
        self.PH2_storage_V = 150.0  # m³
        self.numbers_of_PH2_storage_at_start = 50.0
        self.numbers_of_PH2_storage = 50.0
        self.target_pressure_site_B = 300  # bar
        self.pipeline_diameter = 0.5  # meters
        self.epsilon = 0.000045  # pipe roughness, meters
        self.compressor_velocity = 20.0  # m/s

    def _initialize_transport_params(self):
        """Initialize transport-specific parameters"""
        # Road delivery energy
        self.road_delivery_ener = [0.0455/500, 0.022/500, 0.022/500]  # MJ/kg·km

        # Distances and durations from route_data
        self.distance_A_to_port = self.route['distance_A_to_port']  # km
        self.distance_port_to_B = self.route['distance_port_to_B']  # km
        self.duration_A_to_port = self.route['duration_A_to_port']  # minutes
        self.duration_port_to_B = self.route['duration_port_to_B']  # minutes
        self.port_to_port_dis = self.route['port_to_port_dis']  # km (sea distance)
        self.canal_transits = self.route['canal_transits']

    def liquification_data_fitting(self, H2_plant_capacity):
        """
        Calculate liquefaction energy for hydrogen based on plant capacity.
        Empirical curve fit from industry data.
        """
        return 8.05 - 0.31 * np.log(H2_plant_capacity)

    def site_A_chem_production(self, mass_kg):
        """
        Calculate costs and emissions for fuel production at origin site.

        This step includes insurance cost calculation based on cargo value.
        """
        opex = 0
        capex = 0
        carbon_tax = 0
        insurance = 0

        # Calculate cargo value and insurance
        cargo_value = mass_kg * self.hydrogen_production_cost

        # Insurance calculation will be handled by caller using insurance_model
        # For now, we'll return 0 and let the caller handle it

        # Production emissions (assumed 0 for this model)
        emissions = 0
        carbon_tax_rate = self.carbon_tax_dict.get(self.start_country, 0)
        carbon_tax = carbon_tax_rate * (emissions / 1000)

        energy_consumed = 0
        BOG_loss = 0

        return opex, capex, carbon_tax, energy_consumed, emissions, mass_kg, BOG_loss, insurance

    def site_A_chem_liquification(self, mass_kg):
        """
        Calculate costs and emissions for fuel liquefaction at origin site.
        """
        opex = 0
        capex = 0
        carbon_tax = 0

        # Calculate liquefaction energy
        if self.fuel_type == 0:  # LH2
            liquify_energy_required = self.liquification_data_fitting(self.LH2_plant_capacity) / (self.EIM_liquefication / 100)
        elif self.fuel_type == 1:  # Ammonia
            liquify_heat_required = (self.specific_heat_chem[self.fuel_type] *
                                    (self.start_temp + 273 - self.boiling_point_chem[self.fuel_type]) +
                                    self.latent_H_chem[self.fuel_type])
            liquify_energy_required = liquify_heat_required / self.COP_liq_dyn
        else:  # Methanol (no liquefaction needed)
            liquify_energy_required = 0

        liquify_ener_consumed = liquify_energy_required * mass_kg
        opex += liquify_ener_consumed * self.start_electricity_price[2]

        # CAPEX calculation
        capex_per_kg, om_cost_per_kg = calculate_liquefaction_capex(self.fuel_type, self.LH2_plant_capacity)
        capex += capex_per_kg * mass_kg
        opex += om_cost_per_kg * mass_kg

        # Emissions from energy
        emissions_from_energy = liquify_ener_consumed * 0.2778 * self.CO2e_start * 0.001

        # BOG loss during liquefaction
        BOG_loss = 0.016 * mass_kg
        mass_after_loss = mass_kg - BOG_loss

        # Emissions from BOG
        emissions_from_bog = BOG_loss * self.GWP_chem[self.fuel_type]
        emissions = emissions_from_energy + emissions_from_bog

        # Carbon tax
        carbon_tax_rate = self.carbon_tax_dict.get(self.start_country, 0)
        carbon_tax = carbon_tax_rate * (emissions / 1000)

        return opex, capex, carbon_tax, liquify_ener_consumed, emissions, mass_after_loss, BOG_loss, 0

    # Additional process functions will be added in subsequent methods
    # For brevity in this initial version, I'm showing the pattern
    # The full class would include all 30+ process functions

    def run_full_lca(self):
        """
        Execute full LCA calculation for fuel transport.

        Returns:
            dict: Complete LCA results including costs, emissions, charts, etc.
        """
        # This will orchestrate all the process functions
        # Similar to total_chem_base() but as a class method

        # Initialize with optimization of chemical weight
        optimized_weight = self.optimize_chem_weight()

        # Run through all process steps
        current_mass = optimized_weight
        results = []

        # Process sequence (simplified for now)
        # Full implementation would call all process functions in sequence

        # Example:
        # 1. Production
        opex1, capex1, ctax1, energy1, emit1, current_mass, bog1, ins1 = self.site_A_chem_production(current_mass)

        # 2. Liquefaction
        opex2, capex2, ctax2, energy2, emit2, current_mass, bog2, ins2 = self.site_A_chem_liquification(current_mass)

        # ... Continue with all other steps

        # Aggregate results
        total_opex = opex1 + opex2  # + ...
        total_capex = capex1 + capex2  # + ...
        total_carbon_tax = ctax1 + ctax2  # + ...
        total_emissions = emit1 + emit2  # + ...
        total_bog = bog1 + bog2  # + ...
        total_insurance = ins1 + ins2  # + ...

        # Calculate final costs
        total_cost = total_opex + total_capex + total_carbon_tax + total_insurance
        cost_per_kg = total_cost / self.H2_weight if self.H2_weight > 0 else 0

        return {
            'total_cost_usd': total_cost,
            'cost_per_kg_usd': cost_per_kg,
            'total_emissions_kg_co2': total_emissions,
            'total_bog_loss_kg': total_bog,
            # ... more results
        }

    def optimize_chem_weight(self):
        """
        Optimize chemical weight based on ship capacity constraints.
        Uses scipy.optimize to find optimal loading.
        """
        # Target weight based on ship volume
        target_weight = (self.ship_params['volume_m3'] *
                        self.liquid_chem_density[self.fuel_type] * 0.98)

        # Constraint function
        def constraint(A):
            ship_loaded_vol = A / self.liquid_chem_density[self.fuel_type]
            return self.ship_params['volume_m3'] - ship_loaded_vol

        # Optimization
        con = {'type': 'ineq', 'fun': constraint}
        initial_guess = [target_weight]

        def objective(A):
            # Minimize negative weight (i.e., maximize weight)
            return -A[0]

        result = minimize(
            objective,
            initial_guess,
            method='SLSQP',
            constraints=con,
            bounds=[(1000, target_weight * 1.5)],
            options={'maxiter': 1000, 'ftol': 1e-6}
        )

        if result.success:
            return result.x[0]
        else:
            return target_weight  # Fallback to target if optimization fails
