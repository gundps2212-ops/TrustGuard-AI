from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def render_trustguard_hero(height: int = 510) -> None:
    """Render an isolated Three.js hero scene; does not touch app state or data."""
    html = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  *{box-sizing:border-box}
  html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
  #stage{position:relative;width:100%;height:490px;overflow:hidden;border:1px solid rgba(71,190,255,.20);border-radius:24px;background:radial-gradient(ellipse at 50% 45%,rgba(0,139,210,.20),transparent 42%),linear-gradient(135deg,#061323 0%,#071a2d 48%,#06101e 100%);isolation:isolate}
  #stage:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.22;background-image:linear-gradient(rgba(75,174,220,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(75,174,220,.10) 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(to bottom,black,transparent 92%)}
  #scene{position:absolute;inset:0;width:100%;height:100%;display:block}
  .hud{position:absolute;z-index:2;pointer-events:none;color:#e8f8ff}
  .eyebrow{top:25px;left:28px;font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:#60d8ff;font-weight:800}
  .headline{top:48px;left:28px;max-width:310px;font-size:clamp(22px,3vw,34px);line-height:1.08;font-weight:800;letter-spacing:-.04em;text-shadow:0 0 28px rgba(0,190,255,.18)}
  .headline span{color:#62dcff}
  .sub{top:128px;left:29px;max-width:255px;color:#91b6cc;font-size:12px;line-height:1.6}
  .pill{display:inline-flex;align-items:center;gap:7px;margin-top:13px;padding:7px 10px;border:1px solid rgba(59,218,255,.28);border-radius:99px;background:rgba(4,30,49,.65);font-size:10px;letter-spacing:.08em;color:#bcefff}
  .dot{width:6px;height:6px;border-radius:50%;background:#42f5c5;box-shadow:0 0 12px #42f5c5}
  .right{right:25px;top:27px;text-align:right}
  .metric{font-size:10px;color:#79a9c1;letter-spacing:.15em;text-transform:uppercase}
  .metric b{display:block;margin-top:5px;color:#e8faff;font-size:17px;letter-spacing:0}
  .bottom{left:28px;right:28px;bottom:20px;display:flex;justify-content:space-between;align-items:end;gap:10px}
  .bottom small{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#6f9ab4}
  .legend{display:flex;gap:13px;flex-wrap:wrap;justify-content:flex-end}
  .legend span{font-size:9px;color:#a9c9d9;letter-spacing:.06em}
  .legend i{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:5px;box-shadow:0 0 8px currentColor}
  #fallback{position:absolute;inset:0;display:grid;place-items:center;color:#b8eaff;font-size:13px}
  @media(max-width:620px){#stage{height:450px}.headline{top:52px;max-width:235px}.sub{top:132px;max-width:210px}.right{top:auto;bottom:75px}.bottom{bottom:14px}.legend{gap:7px}}
  @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>
</head>
<body>
<div id="stage">
  <canvas id="scene"></canvas>
  <div id="fallback">Initializing TrustGuard visual engine…</div>
  <div class="hud eyebrow">TRUSTGUARD / INTELLIGENCE CORE</div>
  <div class="hud headline">Truth, powered by<br><span>intelligence.</span></div>
  <div class="hud sub">Multi-layer verification engine for AI-generated claims, evidence and source reliability.</div>
  <div class="hud"><div class="pill"><i class="dot"></i> SYSTEM ONLINE&nbsp; • &nbsp;3D NEURAL CORE</div></div>
  <div class="hud right">
    <div class="metric">Verification layers<b>03 ACTIVE</b></div>
    <div class="metric" style="margin-top:17px">Signal status<b style="color:#42f5c5">NOMINAL</b></div>
  </div>
  <div class="hud bottom">
    <small>AI BRAIN&nbsp; / &nbsp;CORE REACTOR&nbsp; / &nbsp;TRUST SHIELD</small>
    <div class="legend">
      <span><i style="color:#55dfff;background:#55dfff"></i>NEURAL</span>
      <span><i style="color:#4c9dff;background:#4c9dff"></i>VERIFY</span>
      <span><i style="color:#42f5c5;background:#42f5c5"></i>PROTECT</span>
    </div>
  </div>
</div>
<script type="module">
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

const stage=document.getElementById('stage');
const canvas=document.getElementById('scene');
const fallback=document.getElementById('fallback');
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let renderer,scene,camera,brain,core,shield,particles,network,frame=0;
const pointer={x:0,y:0,tx:0,ty:0};
try{
  renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.7));
  renderer.setSize(stage.clientWidth,stage.clientHeight,false);
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  scene=new THREE.Scene();
  camera=new THREE.PerspectiveCamera(38,stage.clientWidth/stage.clientHeight,.1,100);
  camera.position.set(0,0,9.3);
  scene.add(new THREE.AmbientLight(0x75cfff,1.25));
  const key=new THREE.PointLight(0x24cfff,32,18);key.position.set(2,3,5);scene.add(key);
  const rim=new THREE.PointLight(0x246dff,25,16);rim.position.set(-4,-2,2);scene.add(rim);

  const rig=new THREE.Group();scene.add(rig);
  brain=new THREE.Group();brain.position.set(.15,.05,0);rig.add(brain);
  const brainMat=new THREE.MeshStandardMaterial({color:0x2a9ecb,metalness:.48,roughness:.24,transparent:true,opacity:.24,emissive:0x063c65,emissiveIntensity:1.5});
  const left=new THREE.Mesh(new THREE.IcosahedronGeometry(1.12,4),brainMat);
  left.scale.set(.83,1.05,.76);left.position.x=-.48;brain.add(left);
  const rightLobe=left.clone();rightLobe.position.x=.48;brain.add(rightLobe);
  const wireMat=new THREE.MeshBasicMaterial({color:0x57dfff,wireframe:true,transparent:true,opacity:.30});
  const wire=new THREE.Mesh(new THREE.IcosahedronGeometry(1.16,3),wireMat);wire.scale.set(1.12,1.02,.82);brain.add(wire);

  // Neural nodes and connecting synapses distributed on a brain-like ellipsoid.
  const nodePositions=[];
  for(let i=0;i<92;i++){
    const u=Math.random()*Math.PI*2,v=Math.acos(2*Math.random()-1);
    const p=new THREE.Vector3(1.42*Math.sin(v)*Math.cos(u),1.18*Math.cos(v),.86*Math.sin(v)*Math.sin(u));
    if(p.x<-.12 || p.x>.12) nodePositions.push(p);
  }
  const nodeGeo=new THREE.BufferGeometry().setFromPoints(nodePositions);
  const nodeMat=new THREE.PointsMaterial({color:0x8cecff,size:.047,transparent:true,opacity:.94,sizeAttenuation:true});
  const nodes=new THREE.Points(nodeGeo,nodeMat);brain.add(nodes);
  const linePositions=[];
  nodePositions.forEach((p,i)=>{for(let j=i+1;j<nodePositions.length;j++){if(p.distanceTo(nodePositions[j])<.56){linePositions.push(p.x,p.y,p.z,nodePositions[j].x,nodePositions[j].y,nodePositions[j].z)}}});
  const lineGeo=new THREE.BufferGeometry();lineGeo.setAttribute('position',new THREE.Float32BufferAttribute(linePositions,3));
  network=new THREE.LineSegments(lineGeo,new THREE.LineBasicMaterial({color:0x32bde9,transparent:true,opacity:.17}));brain.add(network);

  // Central reactor with three independent orbital rings.
  core=new THREE.Group();core.position.set(0,-.05,.45);rig.add(core);
  const coreBall=new THREE.Mesh(new THREE.IcosahedronGeometry(.39,3),new THREE.MeshPhysicalMaterial({color:0x8cecff,metalness:.3,roughness:.12,emissive:0x0878c5,emissiveIntensity:2.3,clearcoat:1}));
  core.add(coreBall);
  const ringMat=new THREE.MeshBasicMaterial({color:0x45dfff,transparent:true,opacity:.82});
  for(let i=0;i<3;i++){
    const ring=new THREE.Mesh(new THREE.TorusGeometry(.69+i*.17,.012,8,120),ringMat);
    ring.rotation.set(.7+i*.45,.3+i*.38,.2);core.add(ring);
  }
  const halo=new THREE.Mesh(new THREE.SphereGeometry(.95,32,32),new THREE.MeshBasicMaterial({color:0x168cff,wireframe:true,transparent:true,opacity:.09}));core.add(halo);

  // A translucent shield silhouette in front of the core.
  const shape=new THREE.Shape();
  shape.moveTo(0,1.03);shape.quadraticCurveTo(.56,.83,.78,.72);shape.lineTo(.68,-.18);shape.quadraticCurveTo(.55,-.78,0,-1.08);shape.quadraticCurveTo(-.55,-.78,-.68,-.18);shape.lineTo(-.78,.72);shape.quadraticCurveTo(-.56,.83,0,1.03);
  const shieldGeo=new THREE.ShapeGeometry(shape,36);
  shield=new THREE.Group();shield.position.set(1.62,-.03,.9);shield.scale.set(.62,.72,.62);rig.add(shield);
  const shieldMesh=new THREE.Mesh(shieldGeo,new THREE.MeshPhysicalMaterial({color:0x2bdcff,metalness:.45,roughness:.15,transparent:true,opacity:.17,side:THREE.DoubleSide,emissive:0x063f72,emissiveIntensity:.8}));
  shield.add(shieldMesh);
  const edges=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.ExtrudeGeometry(shape,{depth:.055,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.025,bevelThickness:.02})),new THREE.LineBasicMaterial({color:0x62f4ff,transparent:true,opacity:.88}));
  shield.add(edges);
  const check=new THREE.Group();check.position.z=.11;shield.add(check);
  const checkPts=[new THREE.Vector3(-.25,.02,0),new THREE.Vector3(-.06,-.18,0),new THREE.Vector3(.30,.23,0)];
  const checkGeo=new THREE.BufferGeometry().setFromPoints(checkPts);
  check.add(new THREE.Line(checkGeo,new THREE.LineBasicMaterial({color:0x8dffe0,linewidth:3})));

  // Ambient dust field.
  const dustPos=[];for(let i=0;i<520;i++)dustPos.push((Math.random()-.5)*10,(Math.random()-.5)*6,(Math.random()-.5)*5-1);
  const dustGeo=new THREE.BufferGeometry();dustGeo.setAttribute('position',new THREE.Float32BufferAttribute(dustPos,3));
  particles=new THREE.Points(dustGeo,new THREE.PointsMaterial({color:0x63cfff,size:.018,transparent:true,opacity:.58}));scene.add(particles);

  fallback.style.display='none';
  stage.addEventListener('pointermove',e=>{const r=stage.getBoundingClientRect();pointer.tx=((e.clientX-r.left)/r.width-.5)*2;pointer.ty=((e.clientY-r.top)/r.height-.5)*2;});
  stage.addEventListener('pointerleave',()=>{pointer.tx=0;pointer.ty=0;});
  const resize=()=>{const w=stage.clientWidth,h=stage.clientHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);};
  new ResizeObserver(resize).observe(stage);
  const clock=new THREE.Clock();
  function animate(){
    if(!document.hidden){
      const t=clock.getElapsedTime();
      pointer.x+=(pointer.tx-pointer.x)*.035;pointer.y+=(pointer.ty-pointer.y)*.035;
      rig.rotation.y=pointer.x*.20+Math.sin(t*.22)*.10;
      rig.rotation.x=-pointer.y*.12+Math.sin(t*.3)*.035;
      brain.rotation.y=t*.12;brain.rotation.z=Math.sin(t*.45)*.035;
      core.rotation.y=-t*.42;core.rotation.x=Math.sin(t*.5)*.12;
      shield.rotation.y=Math.sin(t*.6)*.10+pointer.x*.08;
      shield.position.y=-.03+Math.sin(t*.9)*.045;
      particles.rotation.y=t*.018;
      renderer.render(scene,camera);
    }
    frame=requestAnimationFrame(animate);
  }
  if(reduced){renderer.render(scene,camera);}else animate();
  document.addEventListener('visibilitychange',()=>{if(document.hidden)cancelAnimationFrame(frame);else if(!reduced)animate();});
}catch(err){
  fallback.textContent='3D preview unavailable in this browser. Enable WebGL or check your internet connection.';
  console.error('TrustGuard 3D scene:',err);
}
</script>
</body>
</html>
"""
    components.html(html, height=height, scrolling=False)
