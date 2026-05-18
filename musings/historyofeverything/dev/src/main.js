import * as THREE from 'three';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

if (history.scrollRestoration) {
  history.scrollRestoration = 'manual';
}
window.scrollTo(0, 0);

gsap.registerPlugin(ScrollTrigger);

// Clean up old videos on hot reload (Vite quirk)
document.querySelectorAll('video').forEach(v => v.remove());

const timelineData = [
  { id: 'void', date: '13.8 Billion Years Ago', title: 'The Void', description: 'Absolute nothingness.', blocks: 1 },
  { id: 'big-bang', date: '13.8 Billion Years Ago', title: 'The Big Bang', description: 'A blinding flash from an infinitely dense point.', blocks: 1 },
  { id: 'cmb', date: '13.8 Billion Years Ago', title: 'Cosmic Microwave Background', description: 'The first light broke free, leaving a cosmic afterglow.', blocks: 4 },
  { id: 'galaxies', date: '13.4 Billion Years Ago', title: 'Formation of Galaxies', description: 'Gravity spun vast clouds of gas and dark matter into majestic galaxies.', blocks: 4 },
  { id: 'solar-system', date: '4.6 Billion Years Ago', title: 'Birth of the Solar System', description: 'A massive star ignited, surrounded by a swirling disk of planetary debris.', blocks: 4 },
  { id: 'hadean', date: '4.5 Billion Years Ago', title: 'The Hadean Earth', description: 'Our planet was a hellish, endless ocean of sloshing molten rock.', blocks: 4 },
  { id: 'rain', date: '4.0 Billion Years Ago', title: 'The Great Rain', description: 'As the surface cooled, centuries of relentless, torrential rain fell.', blocks: 4 },
  { id: 'life', date: '3.8 Billion Years Ago', title: 'First Life', description: 'In the primordial oceans, the first microscopic life emerged.', blocks: 4 },
  { id: 'oxygen', date: '2.4 Billion Years Ago', title: 'The Great Oxidation', description: 'Early life breathed sunlight, flooding the atmosphere with oxygen.', blocks: 4 },
  { id: 'complex', date: '1.5 Billion Years Ago', title: 'The Complex Life', description: 'Cells joined forces, paving the way for multi-cellular organisms.', blocks: 4 },
  { id: 'cambrian', date: '541 Million Years Ago', title: 'The Cambrian Explosion', description: 'An unprecedented burst of evolutionary creativity filled the oceans.', blocks: 4 },
  { id: 'land', date: '400 Million Years Ago', title: 'Conquering the Land', description: 'Life crawled out of the oceans, and vast, realistic forests took root.', blocks: 1 },
  { id: 'dinosaurs', date: '240 Million Years Ago', title: 'Age of Reptiles', description: 'Giant creatures roamed the lush, detailed continents.', blocks: 1 },
  { id: 'asteroid', date: '66 Million Years Ago', title: 'The Extinction', description: 'A massive asteroid struck, sending a shockwave across the globe.', blocks: 1 },
  { id: 'humans', date: '300,000 Years Ago', title: 'The Human Era', description: 'We emerged from the ashes, eventually lighting up the darkness.', blocks: 1 }
];

let totalBlocks = 0;
timelineData.forEach(s => {
  if (!s.blocks) s.blocks = 1;
  s.startBlock = totalBlocks;
  totalBlocks += s.blocks;
});

const textContainer = document.getElementById('text-container');
const timelineNav = document.getElementById('timeline-nav');
const scrollProxy = document.getElementById('scroll-proxy');
scrollProxy.style.height = `${totalBlocks * 100}vh`;

timelineData.forEach((section, index) => {
  const el = document.createElement('div');
  el.className = 'timeline-section';
  el.id = `text-${section.id}`;
  el.innerHTML = `<span class="date-label">${section.date}</span><h2>${section.title}</h2><p>${section.description}</p>`;
  textContainer.appendChild(el);

  const dot = document.createElement('div');
  dot.className = 'nav-dot';
  if (index === 0) dot.classList.add('active');
  dot.innerHTML = `<span class="nav-dot-label">${section.title}</span>`;
  dot.addEventListener('click', () => { window.scrollTo({ top: index * window.innerHeight, behavior: 'smooth' }); });
  timelineNav.appendChild(dot);
});

const sectionElements = document.querySelectorAll('.timeline-section');
const navDots = document.querySelectorAll('.nav-dot');

const canvas = document.getElementById('webgl-canvas');
document.body.style.backgroundColor = '#000000';
const scene = new THREE.Scene();
scene.background = null; // Let the HTML background (or video) show through
scene.fog = new THREE.Fog(0x000000, 100, 1000);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 10000);
camera.position.set(0, 0, 100);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const textureLoader = new THREE.TextureLoader();

const createSoftParticle = () => {
  const c = document.createElement('canvas');
  c.width = 64; c.height = 64;
  const ctx = c.getContext('2d');
  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.2, 'rgba(255,255,255,0.8)');
  gradient.addColorStop(0.5, 'rgba(255,255,255,0.2)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient; ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
};
const particleTexture = createSoftParticle();

const noise3DGLSL = `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v) {
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 = v - i + dot(i, C.xxx) ;
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute( permute( permute( i.z + vec4(0.0, i1.z, i2.z, 1.0 )) + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
  float n_ = 0.142857142857;
  vec3  ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_ );
  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4( x.xy, y.xy );
  vec4 b1 = vec4( x.zw, y.zw );
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
  vec3 p0 = vec3(a0.xy,h.x);
  vec3 p1 = vec3(a0.zw,h.y);
  vec3 p2 = vec3(a1.xy,h.z);
  vec3 p3 = vec3(a1.zw,h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
}
`;

const sceneObjects = {
  bigBangFlash: null,
  bigBangParticles: null,
  cmbSphere: null,
  galaxiesGroup: new THREE.Group(),
  galaxy: null,
  bgGalaxies: [],
  solarSystem: new THREE.Group(),
  earthGroup: new THREE.Group()
};

// 1. Big Bang
sceneObjects.bigBangFlash = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 }));
scene.add(sceneObjects.bigBangFlash);

const bbGeo = new THREE.BufferGeometry();
const bbPos = new Float32Array(30000 * 3);
const bbVel = new Float32Array(30000 * 3);
for(let i=0; i<90000; i+=3) {
  bbPos[i] = 0; bbPos[i+1] = 0; bbPos[i+2] = 0;
  const u = Math.random(), v = Math.random();
  const theta = u * 2.0 * Math.PI, phi = Math.acos(2.0 * v - 1.0);
  const speed = Math.random() * 80 + 20;
  bbVel[i] = Math.sin(phi) * Math.cos(theta) * speed;
  bbVel[i+1] = Math.sin(phi) * Math.sin(theta) * speed;
  bbVel[i+2] = Math.cos(phi) * speed;
}
bbGeo.setAttribute('position', new THREE.BufferAttribute(bbPos, 3));
bbGeo.setAttribute('velocity', new THREE.BufferAttribute(bbVel, 3));
const bbMat = new THREE.PointsMaterial({ size: 2.0, color: 0xffeebb, map: particleTexture, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
sceneObjects.bigBangParticles = new THREE.Points(bbGeo, bbMat);
scene.add(sceneObjects.bigBangParticles);

// Background Videos (HTML5 Overlay - Scroll Bound)
const createBgVideo = (id, src) => {
  const v = document.createElement('video');
  v.id = id; v.src = src; v.crossOrigin = 'anonymous';
  v.loop = true; v.muted = true; v.volume = 0; v.playsInline = true;
  Object.assign(v.style, {
    position: 'fixed', top: '0', left: '0', width: '100vw', height: '100vh',
    objectFit: 'cover', zIndex: '-2', opacity: '0'
  });
  document.body.appendChild(v);
  v.load();
  v.pause(); // Video will be scrubbed via scroll
  return v;
};

const cmbVideo = createBgVideo('cmb-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/cmb.mp4');
const galaxyVideo = createBgVideo('galaxy-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/galaxy.mp4');
const solarVideo = createBgVideo('solar-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/solar_system.mp4');
const hadeanVideo = createBgVideo('hadean-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/hadean.mp4');
const rainVideo = createBgVideo('rain-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/great_rain.mp4');
const lifeVideo = createBgVideo('life-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/first_life.mp4');
const oxygenVideo = createBgVideo('oxygen-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/greatoxidation.mp4');
const complexVideo = createBgVideo('complex-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/complexlife.mp4');
const cambrianVideo = createBgVideo('cambrian-video', 'https://pub-170eae4c8bc147fc842e785bd09533e3.r2.dev/cambrianexplosion.mp4');

const allVideos = [cmbVideo, galaxyVideo, solarVideo, hadeanVideo, rainVideo, lifeVideo, oxygenVideo, complexVideo, cambrianVideo];
const videoTargets = { cmb: 0, galaxy: 0, solar: 0, hadean: 0, rain: 0, life: 0, oxygen: 0, complex: 0, cambrian: 0 };



// 5-12. Earth Horizon (Hyper-Realistic Procedural Shaders)
const earthRadius = 2000;
const earthGeo = new THREE.SphereGeometry(earthRadius, 512, 512); 
const earthHorizonMat = new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 }, uState: { value: 0.0 }, uAsteroidImpact: { value: 0.0 }, uImpactPos: { value: new THREE.Vector3(0,0,0) } },
  vertexShader: `
    varying vec3 vPosition; varying vec3 vNormal; varying vec3 vWorldPos;
    void main() { 
      vNormal = normalize(normalMatrix * normal); vPosition = position;
      vec4 worldPosition = modelMatrix * vec4(position, 1.0);
      vWorldPos = worldPosition.xyz;
      gl_Position = projectionMatrix * viewMatrix * worldPosition; 
    }
  `,
  fragmentShader: `
    uniform float uTime; uniform float uState; uniform float uAsteroidImpact; uniform vec3 uImpactPos;
    varying vec3 vPosition; varying vec3 vNormal; varying vec3 vWorldPos;

    ${noise3DGLSL}
    
    float fbm3d(vec3 p) {
      float f = 0.0; float w = 0.5;
      for (int i=0; i<6; i++) { f += w * snoise(p); p *= 2.0; w *= 0.5; }
      return f * 0.5 + 0.5;
    }
    
    float ridge(float h, float offset) { h = abs(h); h = offset - h; h = h * h; return h; }
    float ridgedFBM3d(vec3 p) {
      float f = 0.0; float w = 0.5;
      for (int i=0; i<5; i++) { f += w * ridge(snoise(p), 1.0); p *= 2.0; w *= 0.5; }
      return f;
    }

    void main() {
      vec3 posNorm = normalize(vPosition);
      
      float elevation = fbm3d(posNorm * 5.0);
      float mountains = ridgedFBM3d(posNorm * 10.0);
      float finalGeo = mix(elevation, mountains, smoothstep(0.5, 0.8, elevation));
      
      vec3 sloshPos = posNorm + vec3(sin(uTime*0.5 + posNorm.y*5.0), cos(uTime*0.6 + posNorm.x*5.0), 0.0) * 0.05;
      float lavaNoise = fbm3d(sloshPos * 15.0);
      vec3 cLava = mix(vec3(0.8, 0.1, 0.0), vec3(1.0, 0.9, 0.2), pow(lavaNoise, 2.0));
      cLava = mix(cLava, vec3(0.05), smoothstep(0.4, 0.8, elevation));

      vec3 cRock = mix(vec3(0.05), vec3(0.3), mountains);
      vec3 cOcean = mix(vec3(0.0, 0.05, 0.2), vec3(0.0, 0.1, 0.4), finalGeo);
      vec3 cOxyOcean = mix(vec3(0.0, 0.1, 0.4), vec3(0.0, 0.3, 0.7), finalGeo);
      
      vec3 cSand = vec3(0.7, 0.6, 0.4);
      vec3 cForest = mix(vec3(0.05, 0.2, 0.05), vec3(0.0, 0.1, 0.0), fbm3d(posNorm * 30.0));
      vec3 cMountainTop = vec3(0.8, 0.8, 0.8);
      
      vec3 cLand = cOxyOcean;
      if (finalGeo > 0.52) cLand = cSand;
      if (finalGeo > 0.54) cLand = cForest;
      if (finalGeo > 0.85) cLand = mix(cForest, cMountainTop, smoothstep(0.85, 0.95, finalGeo));

      float dinoShadows = smoothstep(0.55, 0.6, finalGeo) * snoise(posNorm * 50.0 + uTime * 0.5);
      vec3 cDino = mix(cLand, vec3(0.02, 0.03, 0.02), dinoShadows > 0.6 ? 0.8 : 0.0);
      vec3 cBurnt = mix(vec3(0.02), vec3(0.1), finalGeo);

      float popDensity = smoothstep(0.55, 0.7, finalGeo) * pow(fbm3d(posNorm * 40.0), 3.0);
      vec3 cNight = mix(cOxyOcean * 0.05, mix(vec3(0.01, 0.02, 0.01), vec3(1.0, 0.9, 0.6), popDensity * 15.0), smoothstep(0.52, 0.55, finalGeo));

      vec3 color = cLava;
      if (uState < 1.0) color = mix(cLava, cRock, uState);
      else if (uState < 2.0) color = mix(cRock, cOcean, uState - 1.0);
      else if (uState < 3.0) color = mix(cOcean, cOxyOcean, uState - 2.0);
      else if (uState < 4.0) color = mix(cOxyOcean, cLand, uState - 3.0);
      else if (uState < 5.0) color = mix(cLand, cDino, uState - 4.0);
      else if (uState < 6.0) color = mix(cDino, cBurnt, uState - 5.0);
      else color = mix(cBurnt, cNight, uState - 6.0);

      if (uAsteroidImpact > 0.0 && uAsteroidImpact < 1.0) {
        float distToImpact = distance(vWorldPos, uImpactPos);
        float maxDist = 2000.0; 
        float waveRadius = uAsteroidImpact * maxDist;
        float waveThickness = 50.0;
        
        if (distToImpact < waveRadius && distToImpact > waveRadius - waveThickness) {
           float intensity = 1.0 - uAsteroidImpact;
           color = mix(color, vec3(1.0, 0.4, 0.0) * 2.0, intensity); 
        }
        if (distToImpact < 100.0) {
           color = mix(color, vec3(0.0), smoothstep(100.0, 0.0, distToImpact) * uAsteroidImpact);
        }
      }

      gl_FragColor = vec4(color, 1.0);
    }
  `
});
const earthMesh = new THREE.Mesh(earthGeo, earthHorizonMat);
earthMesh.position.set(0, -earthRadius - 40, 0); 
sceneObjects.earthGroup.add(earthMesh);

const rainCount = 15000;
const rainGeo = new THREE.BufferGeometry();
const rainPos = new Float32Array(rainCount * 6);
for(let i=0; i<rainCount; i++) {
  const x = (Math.random() - 0.5) * 600;
  const y = Math.random() * 200;
  const z = (Math.random() - 0.5) * 300 - 50;
  rainPos[i*6] = x; rainPos[i*6+1] = y; rainPos[i*6+2] = z;
  rainPos[i*6+3] = x; rainPos[i*6+4] = y - 8; rainPos[i*6+5] = z;
}
rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPos, 3));
const rainMat = new THREE.LineBasicMaterial({ color: 0x88bbff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending });
const rainLines = new THREE.LineSegments(rainGeo, rainMat);
sceneObjects.earthGroup.add(rainLines);

const asteroidGeo = new THREE.SphereGeometry(3, 32, 32);
const asteroidMat = new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 }, uOpacity: { value: 0 } },
  vertexShader: `varying vec3 vPos; void main() { vPos = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `
    uniform float uTime; uniform float uOpacity; varying vec3 vPos;
    ${noise3DGLSL}
    void main() {
      float n = snoise(vPos * 2.0 + uTime * 20.0);
      vec3 color = mix(vec3(1.0, 0.1, 0.0), vec3(1.0, 0.9, 0.2), n * 0.5 + 0.5);
      gl_FragColor = vec4(color, uOpacity);
    }
  `, transparent: true, blending: THREE.AdditiveBlending
});
const asteroid = new THREE.Mesh(asteroidGeo, asteroidMat);

const tailGeo = new THREE.ConeGeometry(4, 40, 32);
tailGeo.translate(0, 20, 0); 
const tailMat = new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 }, uOpacity: { value: 0 } },
  vertexShader: `varying vec2 vUv; varying vec3 vPos; void main() { vUv = uv; vPos = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `
    uniform float uTime; uniform float uOpacity; varying vec2 vUv; varying vec3 vPos;
    ${noise3DGLSL}
    void main() {
      float n = snoise(vec3(vUv.x * 10.0, vUv.y * 5.0 - uTime * 30.0, 0.0));
      float alpha = smoothstep(1.0, 0.2, vUv.y) * (n * 0.5 + 0.5);
      vec3 color = mix(vec3(1.0, 0.0, 0.0), vec3(1.0, 0.8, 0.1), 1.0 - vUv.y);
      gl_FragColor = vec4(color, alpha * uOpacity);
    }
  `, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false
});
const asteroidTail = new THREE.Mesh(tailGeo, tailMat);
asteroidTail.rotation.x = -Math.PI / 2;
asteroid.add(asteroidTail);
sceneObjects.earthGroup.add(asteroid);

const flashMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
const impactFlash = new THREE.Mesh(new THREE.PlaneGeometry(1000, 1000), flashMat);
impactFlash.position.z = 90;
sceneObjects.earthGroup.add(impactFlash);

sceneObjects.earthGroup.visible = false;
scene.add(sceneObjects.earthGroup);

// ==========================================
// ANIMATION & SCROLL LOGIC
// ==========================================
let currentSection = 0;
let bigBangTriggered = false;

gsap.set(sectionElements, { opacity: 0, y: 50, visibility: 'hidden' });
gsap.set(sectionElements[0], { opacity: 1, y: 0, visibility: 'visible' });

ScrollTrigger.create({
  trigger: '#scroll-proxy',
  start: 'top top',
  end: 'bottom bottom',
  scrub: 1,
  onUpdate: (self) => {
    const progress = self.progress;
    const currentBlock = progress * totalBlocks;
    
    let newSection = 0;
    for(let i = 0; i < timelineData.length; i++) {
      if (currentBlock >= timelineData[i].startBlock && currentBlock < timelineData[i].startBlock + timelineData[i].blocks) {
        newSection = i;
        break;
      }
    }
    if (currentBlock >= totalBlocks) newSection = timelineData.length - 1;
    
    if (newSection !== currentSection) {
      sectionElements.forEach((el, idx) => {
        if (idx !== newSection) {
          gsap.killTweensOf(el);
          gsap.to(el, { opacity: 0, y: -50, duration: 0.3, onComplete: () => gsap.set(el, { visibility: 'hidden' }) });
          navDots[idx].classList.remove('active');
        }
      });
      currentSection = newSection;
      gsap.killTweensOf(sectionElements[currentSection]);
      gsap.set(sectionElements[currentSection], { visibility: 'visible', y: 50 });
      gsap.to(sectionElements[currentSection], { opacity: 1, y: 0, duration: 0.5, delay: 0.2 });
      navDots[currentSection].classList.add('active');
    }
    
    const sectProg = (currentBlock - timelineData[newSection].startBlock) / timelineData[newSection].blocks;
    const totalProg = currentBlock;

    // Scroll-bound video scrubbing targets (applied in animate loop)
    if (cmbVideo.readyState >= 1 && cmbVideo.duration) { videoTargets.cmb = Math.max(0, Math.min(1, (totalProg - 2.0) / 4.0)) * cmbVideo.duration; }
    if (galaxyVideo.readyState >= 1 && galaxyVideo.duration) { videoTargets.galaxy = Math.max(0, Math.min(1, (totalProg - 6.0) / 4.0)) * galaxyVideo.duration; }
    if (solarVideo.readyState >= 1 && solarVideo.duration) { videoTargets.solar = Math.max(0, Math.min(1, (totalProg - 10.0) / 4.0)) * solarVideo.duration; }
    if (hadeanVideo.readyState >= 1 && hadeanVideo.duration) { videoTargets.hadean = Math.max(0, Math.min(1, (totalProg - 14.0) / 4.0)) * hadeanVideo.duration; }
    if (rainVideo.readyState >= 1 && rainVideo.duration) { videoTargets.rain = Math.max(0, Math.min(1, (totalProg - 18.0) / 4.0)) * rainVideo.duration; }
    if (lifeVideo.readyState >= 1 && lifeVideo.duration) { videoTargets.life = Math.max(0, Math.min(1, (totalProg - 22.0) / 4.0)) * lifeVideo.duration; }
    if (oxygenVideo.readyState >= 1 && oxygenVideo.duration) { videoTargets.oxygen = Math.max(0, Math.min(1, (totalProg - 26.0) / 4.0)) * oxygenVideo.duration; }
    if (complexVideo.readyState >= 1 && complexVideo.duration) { videoTargets.complex = Math.max(0, Math.min(1, (totalProg - 30.0) / 4.0)) * complexVideo.duration; }
    if (cambrianVideo.readyState >= 1 && cambrianVideo.duration) { videoTargets.cambrian = Math.max(0, Math.min(1, (totalProg - 34.0) / 4.0)) * cambrianVideo.duration; }

    sceneObjects.earthGroup.visible = newSection >= 11;
    sceneObjects.bigBangParticles.visible = newSection === 1 || newSection === 2;
    sceneObjects.bigBangFlash.visible = newSection === 1;

    if (newSection < 11) {
      camera.position.set(0, 0, 100);
      camera.lookAt(0, 0, 0);
    } else {
      camera.position.set(0, 5, 100);
      camera.lookAt(0, 0, 0);
    }

    if (newSection === 0) {
      bigBangTriggered = false; bbMat.opacity = 0; sceneObjects.bigBangFlash.material.opacity = 0;
      allVideos.forEach(v => v.style.opacity = '0');
      document.body.style.backgroundColor = '#000000';
      scene.fog.color.setHex(0x000000);
    }
    else if (newSection === 1) { 
      if (!bigBangTriggered) {
        bigBangTriggered = true;
        const pos = bbGeo.attributes.position.array;
        for(let i=0; i<pos.length; i++) pos[i] = 0;
        bbGeo.attributes.position.needsUpdate = true;
      }
      if (sectProg < 0.15) {
        sceneObjects.bigBangFlash.scale.setScalar(sectProg * 600 + 1);
        sceneObjects.bigBangFlash.material.opacity = sectProg * 6.0;
      } else {
        sceneObjects.bigBangFlash.material.opacity = Math.max(0, 1.0 - ((sectProg - 0.15) / 0.5));
      }
      bbMat.opacity = sectProg > 0.05 ? 1.0 - sectProg : 0;
      allVideos.forEach(v => v.style.opacity = '0');
    }
    else if (newSection >= 2 && newSection < 11) {
      allVideos.forEach((vid, idx) => {
        if (idx === newSection - 2) {
           vid.style.opacity = Math.min(1, sectProg * 4).toString();
        } else if (idx === newSection - 3) {
           vid.style.opacity = Math.max(0, 1.0 - sectProg * 4).toString();
        } else {
           vid.style.opacity = '0';
        }
      });
    }
    else if (newSection >= 11) { 
      let state = 0;
      let skyColor = new THREE.Color(0x000000);
      earthHorizonMat.uniforms.uAsteroidImpact.value = 0.0;
      impactFlash.material.opacity = 0;
      
      allVideos.forEach((vid, idx) => {
        if (newSection === 11 && idx === 8) {
           vid.style.opacity = Math.max(0, 1.0 - sectProg * 4).toString();
        } else {
           vid.style.opacity = '0';
        }
      });
      
      if (newSection === 11) { 
        state = 3.0 + sectProg; 
        skyColor.lerpColors(new THREE.Color(0x1a2b3c), new THREE.Color(0x4488ff), Math.min(1.0, sectProg * 2.0));
      } else if (newSection === 12) { 
        state = 4.0 + sectProg; skyColor.setHex(0x4488ff);
      } else if (newSection === 13) { 
        state = 5.0 + sectProg; 
        
        if (sectProg > 0.3 && sectProg < 0.6) {
           asteroidMat.uniforms.uOpacity.value = 1; tailMat.uniforms.uOpacity.value = 1;
           const ap = (sectProg - 0.3) / 0.3; 
           asteroid.position.set(100 - ap * 100, 100 - ap * 100, -20);
           asteroid.lookAt(0, -10, -20); 
           skyColor.setHex(0xffaa00); 
        } else if (sectProg >= 0.6) {
           asteroidMat.uniforms.uOpacity.value = 0; tailMat.uniforms.uOpacity.value = 0;
           skyColor.setHex(0x110500); 
           
           if (sectProg < 0.65) {
             impactFlash.material.opacity = 1.0 - (sectProg - 0.6)/0.05;
             skyColor.setHex(0xffffff);
           }
           
           if (sectProg < 0.9) {
             const swProg = (sectProg - 0.6) / 0.3;
             earthHorizonMat.uniforms.uAsteroidImpact.value = swProg;
             earthHorizonMat.uniforms.uImpactPos.value.set(0, 0, -20);
           }
        } else {
           asteroidMat.uniforms.uOpacity.value = 0; tailMat.uniforms.uOpacity.value = 0;
           skyColor.setHex(0x4488ff);
        }
      } else if (newSection === 14) { 
        state = 6.0 + sectProg; 
        skyColor.lerpColors(new THREE.Color(0x110500), new THREE.Color(0x020205), sectProg);
      }

      earthHorizonMat.uniforms.uState.value = state;
      document.body.style.backgroundColor = '#' + skyColor.getHexString();
      scene.fog.color.copy(skyColor);
    }
  }
});

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  const time = clock.getElapsedTime();

  if (bigBangTriggered && bbMat.opacity > 0) {
    const pos = bbGeo.attributes.position.array;
    const vel = bbGeo.attributes.velocity.array;
    for(let i=0; i<pos.length; i+=3) {
      pos[i] += vel[i] * dt; pos[i+1] += vel[i+1] * dt; pos[i+2] += vel[i+2] * dt;
    }
    bbGeo.attributes.position.needsUpdate = true;
  }

  // Smooth video scrubbing logic
  if (!cmbVideo.seeking && Math.abs(cmbVideo.currentTime - videoTargets.cmb) > 0.05) { cmbVideo.currentTime = videoTargets.cmb; }
  if (!galaxyVideo.seeking && Math.abs(galaxyVideo.currentTime - videoTargets.galaxy) > 0.05) { galaxyVideo.currentTime = videoTargets.galaxy; }
  if (!solarVideo.seeking && Math.abs(solarVideo.currentTime - videoTargets.solar) > 0.05) { solarVideo.currentTime = videoTargets.solar; }
  if (!hadeanVideo.seeking && Math.abs(hadeanVideo.currentTime - videoTargets.hadean) > 0.05) { hadeanVideo.currentTime = videoTargets.hadean; }
  if (!rainVideo.seeking && Math.abs(rainVideo.currentTime - videoTargets.rain) > 0.05) { rainVideo.currentTime = videoTargets.rain; }
  if (!lifeVideo.seeking && Math.abs(lifeVideo.currentTime - videoTargets.life) > 0.05) { lifeVideo.currentTime = videoTargets.life; }
  if (!oxygenVideo.seeking && Math.abs(oxygenVideo.currentTime - videoTargets.oxygen) > 0.05) { oxygenVideo.currentTime = videoTargets.oxygen; }
  if (!complexVideo.seeking && Math.abs(complexVideo.currentTime - videoTargets.complex) > 0.05) { complexVideo.currentTime = videoTargets.complex; }
  if (!cambrianVideo.seeking && Math.abs(cambrianVideo.currentTime - videoTargets.cambrian) > 0.05) { cambrianVideo.currentTime = videoTargets.cambrian; }

  if (sceneObjects.earthGroup.visible) {
    earthMesh.rotation.z = time * 0.02; 
    earthHorizonMat.uniforms.uTime.value = time;
    
    if (rainMat.opacity > 0) {
      const rp = rainGeo.attributes.position.array;
      for(let i=0; i<rainCount; i++) {
        rp[i*6+1] -= 300 * dt; 
        rp[i*6+4] -= 300 * dt;
        if (rp[i*6+1] < -50) {
          rp[i*6+1] = 150 + Math.random()*50;
          rp[i*6+4] = rp[i*6+1] - 8;
        }
      }
      rainGeo.attributes.position.needsUpdate = true;
    }
    
    if (asteroidMat.uniforms.uOpacity.value > 0) {
      asteroidMat.uniforms.uTime.value = time;
      tailMat.uniforms.uTime.value = time;
    }
  }

  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
});
