import re

fname = "plot_battery_discharge_window.py"
with open(fname, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('pad=0.01,\n                     aspect=20', 'pad=0.08,\n                     aspect=20')

with open(fname, "w", encoding="utf-8") as f:
    f.write(text)

fname = "plot_peak_lmp_timeshift.py"
with open(fname, "r", encoding="utf-8") as f:
    text = f.read()

old_x = """ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))"""
new_x = """ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))"""
text = text.replace(old_x, new_x)

text = text.replace('pad=0.01, aspect=20', 'pad=0.08, aspect=20')
text = text.replace('pad=0.01, aspect=25', 'pad=0.08, aspect=25')

with open(fname, "w", encoding="utf-8") as f:
    f.write(text)

print("Applied feedback adjustments!")
