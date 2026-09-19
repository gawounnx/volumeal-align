"use client";
import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { FoodItemEstimation, SparsePointCloudPayload } from '../types/vision';
interface Props { items: FoodItemEstimation[]; pointCloud?: SparsePointCloudPayload; height?: number; }
export default function ThreeViewer({ items, pointCloud, height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
    catch { setError('이 브라우저에서 3D 표시를 사용할 수 없습니다.'); return; }
    setError(null);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 100);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.touchAction = 'none';
    container.replaceChildren(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    const group = new THREE.Group();
    // OpenCV camera coordinates: x right, y down, z forward (metres).
    group.scale.set(1, -1, -1);
    const renderedPointCount = Math.min(pointCloud?.count ?? 0, 5000);
    if (pointCloud && pointCloud.positions.length >= renderedPointCount * 3 && pointCloud.colors.length >= renderedPointCount * 3) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(pointCloud.positions.slice(0, renderedPointCount * 3), 3));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(pointCloud.colors.slice(0, renderedPointCount * 3), 3));
      group.add(new THREE.Points(geometry, new THREE.PointsMaterial({ size: 0.003, vertexColors: true })));
    }
    items.forEach(item => {
      const { center, dimensions, rotations } = item.bbox3d;
      const geometry = new THREE.BoxGeometry(dimensions.x, dimensions.y, dimensions.z);
      const edges = new THREE.EdgesGeometry(geometry);
      geometry.dispose();
      const box = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x38bdf8 }));
      box.position.set(center.x, center.y, center.z);
      box.rotation.set(rotations.x, rotations.y, rotations.z);
      group.add(box);
    });
    scene.add(group);
    scene.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(group);
    const center = bounds.isEmpty() ? new THREE.Vector3() : bounds.getCenter(new THREE.Vector3());
    const radius = bounds.isEmpty() ? .3 : Math.max(bounds.getSize(new THREE.Vector3()).length()/2, .05);
    controls.target.copy(center);
    const resize = () => {
      const width = Math.max(container.clientWidth, 1);
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      const halfFov = Math.min(THREE.MathUtils.degToRad(22.5), Math.atan(Math.tan(THREE.MathUtils.degToRad(22.5))*camera.aspect));
      const distance = radius / Math.sin(halfFov) * 1.2;
      camera.position.copy(center).add(new THREE.Vector3(0,.25,1).normalize().multiplyScalar(distance));
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    renderer.domElement.dataset.testid = 'point-cloud-canvas';
    renderer.domElement.dataset.pointCount = String(renderedPointCount);
    renderer.domElement.dataset.renderFps = '60';
    let animationId = 0, frames = 0, sampledAt = performance.now();
    const animate = (now = performance.now()) => { animationId = requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); frames++; if (now - sampledAt >= 1000) { renderer.domElement.dataset.renderFps = String(Math.round(frames * 1000 / (now - sampledAt))); frames = 0; sampledAt = now; } };
    animate();
    return () => {
      cancelAnimationFrame(animationId);
      observer.disconnect();
      controls.dispose();
      scene.traverse(object => {
        const drawable = object as THREE.Mesh;
        drawable.geometry?.dispose();
        if (drawable.material) (Array.isArray(drawable.material) ? drawable.material : [drawable.material]).forEach(material => material.dispose());
      });
      renderer.dispose();
      renderer.forceContextLoss();
      container.replaceChildren();
    };
  }, [items, pointCloud, height]);
  return <div className="relative w-full overflow-hidden rounded-xl border border-slate-700 touch-none">
    <div ref={containerRef} style={{ width: '100%', height }} />
    <div className="absolute top-3 left-3 text-xs text-cyan-300">{error || (items.length ? '추정 점군 · 3D 경계 상자 (m)' : '분석 후 3D 결과가 표시됩니다.')}</div>
    <div className="absolute bottom-3 right-3 text-xs text-slate-400">터치/드래그: 회전 | 핀치: 줌</div>
  </div>;
}
