<template>
  <div ref="containerRef" class="roi-canvas" @mouseleave="hoveredDeleteId = null">
    <img v-if="imageUrl" class="roi-canvas__image" :src="imageUrl" alt="Scene baseline" @load="resizeCanvas" />
    <div v-else class="roi-canvas__placeholder">No baseline image configured</div>
    <canvas
      ref="canvasRef"
      class="roi-canvas__surface"
      :class="{ 'roi-canvas__surface--editable': editable }"
      @click="handleClick"
      @dblclick.prevent="closeDraft"
      @mousemove="handleMouseMove"
    />
    <div class="roi-canvas__hint">
      Click to add points. Double-click to close polygon. Coordinates are normalized.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import type { Roi, RoiGeometry } from '@/api/types';

const props = withDefaults(
  defineProps<{
    rois: Roi[];
    imageUrl?: string | null;
    editable?: boolean;
  }>(),
  {
    imageUrl: null,
    editable: false,
  },
);

const emit = defineEmits<{
  (event: 'roi-created', geometry: RoiGeometry): void;
  (event: 'roi-deleted', id: number): void;
}>();

type Point = [number, number];

interface DeleteHitBox {
  roi: Roi;
  x: number;
  y: number;
  size: number;
}

const palette = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#9b59b6', '#00bcd4'];
const containerRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const draftPoints = ref<Point[]>([]);
const pointer = ref<Point | null>(null);
const hoveredDeleteId = ref<number | null>(null);
const deleteHitBoxes = ref<DeleteHitBox[]>([]);

const normalizedDraft = computed<RoiGeometry>(() => ({
  type: 'polygon',
  points: draftPoints.value,
}));

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function toCanvasPoint(point: Point, canvas: HTMLCanvasElement): Point {
  return [point[0] * canvas.width, point[1] * canvas.height];
}

function getEventPoint(event: MouseEvent): Point | null {
  const canvas = canvasRef.value;
  if (canvas === null) {
    return null;
  }
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    return null;
  }
  return [clamp01((event.clientX - rect.left) / rect.width), clamp01((event.clientY - rect.top) / rect.height)];
}

function drawPolygon(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, points: Point[], color: string, closed: boolean): void {
  if (points.length === 0) {
    return;
  }

  ctx.beginPath();
  points.forEach((point, index) => {
    const [x, y] = toCanvasPoint(point, canvas);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  if (closed) {
    ctx.closePath();
    ctx.fillStyle = `${color}33`;
    ctx.fill();
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();

  points.forEach((point) => {
    const [x, y] = toCanvasPoint(point, canvas);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  });
}

function drawLabel(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, roi: Roi, color: string): void {
  const firstPoint = roi.geometry.points[0];
  if (firstPoint === undefined) {
    return;
  }

  const [x, y] = toCanvasPoint(firstPoint, canvas);
  const label = roi.name;
  ctx.font = '13px sans-serif';
  const width = ctx.measureText(label).width + 30;
  const height = 22;
  const labelX = Math.min(Math.max(4, x), canvas.width - width - 4);
  const labelY = Math.min(Math.max(height + 4, y), canvas.height - 4);
  ctx.fillStyle = color;
  ctx.fillRect(labelX, labelY - height, width, height);
  ctx.fillStyle = '#fff';
  ctx.fillText(label, labelX + 8, labelY - 7);

  const deleteBox: DeleteHitBox = { roi, x: labelX + width - 20, y: labelY - height + 4, size: 14 };
  deleteHitBoxes.value.push(deleteBox);
  ctx.fillStyle = hoveredDeleteId.value === roi.id ? '#f56c6c' : '#ffffff33';
  ctx.fillRect(deleteBox.x, deleteBox.y, deleteBox.size, deleteBox.size);
  ctx.strokeStyle = '#fff';
  ctx.beginPath();
  ctx.moveTo(deleteBox.x + 4, deleteBox.y + 4);
  ctx.lineTo(deleteBox.x + 10, deleteBox.y + 10);
  ctx.moveTo(deleteBox.x + 10, deleteBox.y + 4);
  ctx.lineTo(deleteBox.x + 4, deleteBox.y + 10);
  ctx.stroke();
}

function redraw(): void {
  const canvas = canvasRef.value;
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) {
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  deleteHitBoxes.value = [];
  props.rois.forEach((roi, index) => {
    const color = palette[index % palette.length] ?? palette[0];
    drawPolygon(ctx, canvas, roi.geometry.points, color, true);
    drawLabel(ctx, canvas, roi, color);
  });

  if (draftPoints.value.length > 0) {
    const points = pointer.value === null ? draftPoints.value : [...draftPoints.value, pointer.value];
    drawPolygon(ctx, canvas, points, '#303133', false);
  }
}

function resizeCanvas(): void {
  const canvas = canvasRef.value;
  const container = containerRef.value;
  if (canvas === null || container === null) {
    return;
  }
  const rect = container.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));
  canvas.width = width;
  canvas.height = height;
  redraw();
}

function findDeleteHit(point: Point): Roi | null {
  const canvas = canvasRef.value;
  if (canvas === null) {
    return null;
  }
  const [x, y] = toCanvasPoint(point, canvas);
  const hit = deleteHitBoxes.value.find((box) => x >= box.x && x <= box.x + box.size && y >= box.y && y <= box.y + box.size);
  return hit?.roi ?? null;
}

function handleClick(event: MouseEvent): void {
  const point = getEventPoint(event);
  if (point === null) {
    return;
  }
  const roiToDelete = findDeleteHit(point);
  if (roiToDelete !== null) {
    emit('roi-deleted', roiToDelete.id);
    return;
  }
  if (!props.editable) {
    return;
  }
  draftPoints.value.push(point);
  redraw();
}

function closeDraft(): void {
  if (!props.editable || draftPoints.value.length < 3) {
    return;
  }
  emit('roi-created', normalizedDraft.value);
  draftPoints.value = [];
  pointer.value = null;
  redraw();
}

function handleMouseMove(event: MouseEvent): void {
  const point = getEventPoint(event);
  pointer.value = point;
  hoveredDeleteId.value = point === null ? null : findDeleteHit(point)?.id ?? null;
  redraw();
}

watch(() => props.rois, redraw, { deep: true });
watch(() => props.imageUrl, () => void nextTick(resizeCanvas));
watch(() => props.editable, (enabled) => {
  if (!enabled) {
    draftPoints.value = [];
    pointer.value = null;
    redraw();
  }
});

onMounted(() => {
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas);
});
</script>

<style scoped>
.roi-canvas {
  position: relative;
  width: 100%;
  min-height: 420px;
  overflow: hidden;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #f5f7fa;
}

.roi-canvas__image,
.roi-canvas__surface,
.roi-canvas__placeholder {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.roi-canvas__image {
  object-fit: contain;
}

.roi-canvas__surface {
  cursor: default;
}

.roi-canvas__surface--editable {
  cursor: crosshair;
}

.roi-canvas__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.roi-canvas__hint {
  position: absolute;
  right: 12px;
  bottom: 12px;
  padding: 6px 10px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  background: rgb(0 0 0 / 55%);
}
</style>
