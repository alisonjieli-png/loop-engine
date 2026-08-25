import { showcaseData } from "./showcase-data.js";

const FONT_STACK = "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
const FULL_CIRCLE = Math.PI * 2;

export const timelineSlides = showcaseData.slides.map((slide, index, allSlides) => {
  const startMs = allSlides.slice(0, index).reduce((total, item) => total + item.durationSeconds * 1000, 0);
  const durationMs = slide.durationSeconds * 1000;
  return { ...slide, index, startMs, durationMs, endMs: startMs + durationMs };
});

export const durationMs = timelineSlides.reduce((total, slide) => total + slide.durationMs, 0);

function color(name) {
  return showcaseData.palette[name] || name;
}

function roleStyle(roleName) {
  const role = showcaseData.roles[roleName] || showcaseData.roles.static;
  return { color: color(role.color), soft: color(role.soft), label: role.label };
}

function modeStyle(modeName) {
  return showcaseData.modes[modeName] || showcaseData.modes.deterministic;
}

function roundedRect(ctx, x, y, width, height, radius, fill, stroke, lineWidth = 2) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  if (fill) {
    ctx.fillStyle = fill;
    ctx.fill();
  }
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
  }
}

function setFont(ctx, size, weight = 400) {
  ctx.font = `${weight} ${size}px ${FONT_STACK}`;
}

function splitLines(ctx, text, maxWidth) {
  const paragraphs = String(text).split("\n");
  const lines = [];
  paragraphs.forEach((paragraph, paragraphIndex) => {
    const words = paragraph.split(/\s+/).filter(Boolean);
    let current = "";
    words.forEach((word) => {
      const candidate = current ? `${current} ${word}` : word;
      if (current && ctx.measureText(candidate).width > maxWidth) {
        lines.push(current);
        current = word;
      } else {
        current = candidate;
      }
    });
    if (current) lines.push(current);
    if (paragraphIndex < paragraphs.length - 1) lines.push("");
  });
  return lines;
}

function drawText(ctx, text, x, y, options = {}) {
  const {
    size = 28,
    weight = 400,
    fill = color("ink"),
    maxWidth = 1000,
    lineHeight = 1.22,
    align = "left",
    baseline = "top",
    maxLines = 5,
    alpha = 1
  } = options;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = fill;
  ctx.textAlign = align;
  ctx.textBaseline = baseline;
  setFont(ctx, size, weight);
  const lines = splitLines(ctx, text, maxWidth).slice(0, maxLines);
  lines.forEach((line, index) => {
    ctx.fillText(line, x, y + index * size * lineHeight);
  });
  ctx.restore();
  return lines.length * size * lineHeight;
}

function reveal(progress, index, total) {
  if (globalThis.__showcaseReducedMotion) return 1;
  const start = 0.08 + (index / Math.max(total, 1)) * 0.62;
  return Math.max(0, Math.min(1, (progress - start) / 0.16));
}

function drawArrow(ctx, fromX, fromY, toX, toY, options = {}) {
  const { stroke = color("muted"), label = "", alpha = 1, dashed = false } = options;
  const angle = Math.atan2(toY - fromY, toX - fromX);
  const head = 14;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = stroke;
  ctx.fillStyle = stroke;
  ctx.lineWidth = 3;
  if (dashed) ctx.setLineDash([10, 10]);
  ctx.beginPath();
  ctx.moveTo(fromX, fromY);
  ctx.lineTo(toX, toY);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(toX, toY);
  ctx.lineTo(toX - head * Math.cos(angle - Math.PI / 6), toY - head * Math.sin(angle - Math.PI / 6));
  ctx.lineTo(toX - head * Math.cos(angle + Math.PI / 6), toY - head * Math.sin(angle + Math.PI / 6));
  ctx.closePath();
  ctx.fill();
  if (label) {
    const middleX = (fromX + toX) / 2;
    const middleY = (fromY + toY) / 2 - 24;
    const labelWidth = Math.min(280, Math.max(130, label.length * 12));
    roundedRect(ctx, middleX - labelWidth / 2, middleY - 12, labelWidth, 32, 8, color("paper"), color("line"), 1);
    drawText(ctx, label, middleX, middleY - 5, { size: 17, weight: 700, align: "center", maxWidth: labelWidth - 18, maxLines: 1 });
  }
  ctx.restore();
}

function drawLoop(ctx, x, y, radius, item, alpha = 1) {
  const role = roleStyle(item.role || "static");
  const mode = modeStyle(item.mode || "deterministic");
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = role.soft;
  ctx.strokeStyle = role.color;
  ctx.lineWidth = mode.style === "double" ? 5 : 4;
  ctx.setLineDash(mode.style === "dotted" ? [8, 9] : []);
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, FULL_CIRCLE);
  ctx.fill();
  ctx.stroke();
  ctx.setLineDash([]);
  if (mode.style === "double") {
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, radius - 10, 0, FULL_CIRCLE);
    ctx.stroke();
  }
  drawText(ctx, item.label, x, y - 22, {
    size: radius > 95 ? 25 : 20,
    weight: 750,
    align: "center",
    baseline: "middle",
    maxWidth: radius * 1.55,
    maxLines: 3,
    lineHeight: 1.08
  });
  if (item.profile) {
    drawText(ctx, item.profile, x, y + 42, { size: 16, weight: 600, fill: role.color, align: "center", baseline: "middle", maxWidth: radius * 1.55, maxLines: 1 });
  } else if (item.mode) {
    drawText(ctx, mode.label, x, y + 42, { size: 15, weight: 650, fill: role.color, align: "center", baseline: "middle", maxWidth: radius * 1.55, maxLines: 2 });
  }
  ctx.restore();
}

function drawCard(ctx, x, y, width, height, item, alpha = 1) {
  const role = roleStyle(item.role || "static");
  ctx.save();
  ctx.globalAlpha = alpha;
  roundedRect(ctx, x, y, width, height, 20, item.fill || role.soft, item.stroke || role.color, 2);
  if (item.tag) {
    drawText(ctx, item.tag, x + 24, y + 20, { size: 17, weight: 750, fill: role.color, maxWidth: width - 48, maxLines: 1 });
  }
  const titleY = item.tag ? y + 52 : y + 28;
  drawText(ctx, item.label, x + 24, titleY, { size: item.titleSize || 25, weight: 760, maxWidth: width - 48, maxLines: 2, lineHeight: 1.08 });
  if (item.detail) {
    drawText(ctx, item.detail, x + 24, titleY + 65, { size: 19, fill: color("muted"), maxWidth: width - 48, maxLines: 3 });
  }
  if (item.items) {
    item.items.forEach((entry, index) => {
      const itemY = titleY + 66 + index * 50;
      ctx.fillStyle = role.color;
      ctx.beginPath();
      ctx.arc(x + 31, itemY + 11, 5, 0, FULL_CIRCLE);
      ctx.fill();
      drawText(ctx, entry, x + 49, itemY, { size: 18, fill: color("muted"), maxWidth: width - 75, maxLines: 2 });
    });
  }
  ctx.restore();
}

function drawHeader(ctx, slide) {
  drawText(ctx, slide.kicker, 100, 58, { size: 20, weight: 800, fill: color("static"), maxWidth: 1720, maxLines: 1 });
  drawText(ctx, slide.title, 100, 96, { size: 50, weight: 780, maxWidth: 1720, maxLines: 2, lineHeight: 1.02 });
  drawText(ctx, slide.subtitle, 100, 170, { size: 24, fill: color("muted"), maxWidth: 1720, maxLines: 2, lineHeight: 1.16 });
  ctx.strokeStyle = color("faint");
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(100, 228);
  ctx.lineTo(1820, 228);
  ctx.stroke();
}

function drawAnnotationAndFooter(ctx, slide, index) {
  roundedRect(ctx, 100, 922, 1720, 72, 14, color("staticSoft"), color("line"), 1);
  drawText(ctx, slide.annotation, 128, 943, { size: 19, weight: 550, fill: color("muted"), maxWidth: 1664, maxLines: 2 });
  drawText(ctx, showcaseData.meta.brand, 100, 1024, { size: 17, weight: 650, fill: color("static"), maxWidth: 900, maxLines: 1 });
  const counter = `${showcaseData.ui.slideLabel} ${index + 1} / ${showcaseData.slides.length}`;
  drawText(ctx, counter, 1820, 1024, { size: 17, weight: 650, fill: color("static"), align: "right", maxWidth: 300, maxLines: 1 });
}

function renderTitle(ctx, slide, progress) {
  const centerX = 960;
  const centerY = 500;
  drawLoop(ctx, centerX, centerY, 142, { label: slide.visual.statement, role: "practitioner" }, 1);
  slide.visual.marks.forEach((mark, index) => {
    const positions = [
      { x: 470, y: 690, role: "practitioner" },
      { x: 960, y: 740, role: "intelligence" },
      { x: 1450, y: 690, role: "solution" }
    ];
    const position = positions[index];
    drawLoop(ctx, position.x, position.y, 90, { label: mark, role: position.role }, reveal(progress, index + 1, 4));
    drawArrow(ctx, centerX, centerY + 135, position.x, position.y - 92, { alpha: reveal(progress, index + 1, 4), stroke: roleStyle(position.role).color });
  });
}

function renderOverview(ctx, slide, progress) {
  const visual = slide.visual;
  const intelligenceAlpha = reveal(progress, 0, 4);
  drawCard(ctx, 100, 262, 1040, 174, {
    label: visual.intelligence.label,
    role: visual.intelligence.role,
    items: visual.intelligence.items
  }, intelligenceAlpha);
  const first = visual.flow[0];
  const second = visual.flow[1];
  drawLoop(ctx, 430, 620, 118, first, reveal(progress, 1, 4));
  drawCard(ctx, 790, 520, 360, 200, second, reveal(progress, 2, 4));
  drawArrow(ctx, 552, 620, 790, 620, { label: visual.flow[0].detail, alpha: reveal(progress, 2, 4), stroke: color("practitioner") });
  drawCard(ctx, 1210, 300, 610, 500, { ...visual.staticArchitecture, titleSize: 28 }, reveal(progress, 3, 4));
  drawArrow(ctx, 950, 500, 950, 448, { stroke: color("intelligence"), alpha: intelligenceAlpha });
}

function renderLoopObject(ctx, slide, progress) {
  const visual = slide.visual;
  drawLoop(ctx, 960, 570, 150, { label: visual.loopLabel, role: "practitioner", profile: visual.profileLabel }, reveal(progress, 0, 10));
  drawCard(ctx, 100, 480, 300, 140, { label: visual.input, role: "static" }, reveal(progress, 1, 10));
  drawCard(ctx, 1520, 480, 300, 140, { label: visual.output, role: "static" }, reveal(progress, 2, 10));
  drawArrow(ctx, 400, 550, 802, 550, { stroke: color("static"), alpha: reveal(progress, 2, 10) });
  drawArrow(ctx, 1118, 550, 1520, 550, { stroke: color("static"), alpha: reveal(progress, 2, 10) });
  const positions = [
    [120, 270], [510, 270], [1010, 270], [1400, 270],
    [120, 720], [510, 760], [1010, 760], [1400, 720]
  ];
  visual.fields.forEach((field, index) => {
    const [x, y] = positions[index];
    drawCard(ctx, x, y, 350, 105, { label: field, role: index % 2 ? "static" : "practitioner", titleSize: 21 }, reveal(progress, index + 2, 10));
  });
}

function renderTypedFlow(ctx, slide, progress) {
  const visual = slide.visual;
  const cards = [visual.input, visual.output];
  drawCard(ctx, 100, 420, 390, 240, { label: cards[0].label, tag: cards[0].type, detail: cards[0].example, role: "static" }, reveal(progress, 0, 4));
  drawLoop(ctx, 960, 540, 145, visual.loop, reveal(progress, 1, 4));
  drawCard(ctx, 1430, 420, 390, 240, { label: cards[1].label, tag: cards[1].type, detail: cards[1].example, role: "static" }, reveal(progress, 2, 4));
  drawArrow(ctx, 490, 540, 808, 540, { stroke: color("static"), alpha: reveal(progress, 1, 4) });
  drawArrow(ctx, 1112, 540, 1430, 540, { stroke: color("solution"), alpha: reveal(progress, 2, 4) });
  drawCard(ctx, 660, 760, 600, 90, { label: visual.check, role: "static", titleSize: 21 }, reveal(progress, 3, 4));
}

function renderTwoColumn(ctx, slide, progress) {
  slide.visual.columns.forEach((column, index) => {
    drawCard(ctx, 140 + index * 850, 300, 790, 500, { ...column, titleSize: 32 }, reveal(progress, index, 2));
  });
  drawArrow(ctx, 932, 550, 990, 550, { stroke: color("static"), alpha: reveal(progress, 1, 2) });
}

function renderMode(ctx, slide, progress) {
  const visual = slide.visual;
  const mode = modeStyle(visual.mode);
  drawLoop(ctx, 440, 555, 165, { label: visual.loopLabel, role: "practitioner", mode: visual.mode }, reveal(progress, 0, 5));
  drawCard(ctx, 780, 300, 1040, 390, {
    label: mode.label,
    tag: mode.lead,
    role: visual.mode === "deterministic" ? "static" : "practitioner",
    items: visual.steps,
    titleSize: 35
  }, reveal(progress, 1, 5));
  drawCard(ctx, 780, 730, 1040, 120, { label: visual.control, role: "static", titleSize: 20 }, reveal(progress, 4, 5));
}

function renderComparison(ctx, slide, progress) {
  const { headers, rows } = slide.visual;
  const x = 100;
  const y = 295;
  const widths = [340, 440, 440, 500];
  const rowHeight = 112;
  let cursorX = x;
  headers.forEach((header, index) => {
    roundedRect(ctx, cursorX, y, widths[index], 82, 0, index === 0 ? color("staticSoft") : [color("staticSoft"), color("practitionerSoft"), color("intelligenceSoft")][index - 1], color("line"), 1);
    drawText(ctx, header, cursorX + widths[index] / 2, y + 25, { size: 21, weight: 760, align: "center", maxWidth: widths[index] - 32, maxLines: 2 });
    cursorX += widths[index];
  });
  rows.forEach((row, rowIndex) => {
    let rowX = x;
    row.forEach((cell, columnIndex) => {
      const alpha = reveal(progress, rowIndex, rows.length);
      ctx.save();
      ctx.globalAlpha = alpha;
      roundedRect(ctx, rowX, y + 82 + rowIndex * rowHeight, widths[columnIndex], rowHeight, 0, color("paper"), color("line"), 1);
      drawText(ctx, cell, rowX + 20, y + 111 + rowIndex * rowHeight, { size: columnIndex === 0 ? 21 : 20, weight: columnIndex === 0 ? 720 : 500, fill: columnIndex === 0 ? color("ink") : color("muted"), maxWidth: widths[columnIndex] - 40, maxLines: 3 });
      ctx.restore();
      rowX += widths[columnIndex];
    });
  });
}

function renderHierarchy(ctx, slide, progress) {
  const visual = slide.visual;
  drawLoop(ctx, 960, 420, 86, { label: visual.trunk, role: "static" }, reveal(progress, 0, 4));
  visual.branches.forEach((branch, index) => {
    const x = 110 + index * 580;
    const cardX = x;
    const centerX = x + 530 / 2;
    drawArrow(ctx, 960, 508, centerX, 575, { stroke: roleStyle(branch.role).color, alpha: reveal(progress, index + 1, 4) });
    drawCard(ctx, cardX, 580, 530, 270, { ...branch, titleSize: 30 }, reveal(progress, index + 1, 4));
  });
}

function renderSteps(ctx, slide, progress) {
  const visual = slide.visual;
  drawLoop(ctx, 250, 545, 118, { label: visual.loopLabel, role: "practitioner" }, reveal(progress, 0, visual.steps.length + 1));
  const startX = 460;
  const y = 455;
  visual.steps.forEach((step, index) => {
    const x = startX + index * 268;
    drawCard(ctx, x, y, 220, 180, { label: step, role: "practitioner", titleSize: 22 }, reveal(progress, index + 1, visual.steps.length + 1));
    if (index < visual.steps.length - 1) {
      drawArrow(ctx, x + 220, y + 90, x + 268, y + 90, { stroke: color("practitioner"), alpha: reveal(progress, index + 2, visual.steps.length + 1) });
    }
  });
  drawArrow(ctx, 1788, 665, 250, 665, { label: visual.repeatLabel, dashed: true, stroke: color("improvement"), alpha: reveal(progress, 5, 6) });
  drawCard(ctx, 1470, 720, 340, 90, { label: visual.exitLabel, role: "solution", titleSize: 22 }, reveal(progress, 4, 5));
}

function renderSpawn(ctx, slide, progress) {
  const visual = slide.visual;
  drawLoop(ctx, 430, 550, 142, visual.starting, reveal(progress, 0, 4));
  const positions = [[1050, 430], [1400, 560], [1050, 750]];
  visual.spawned.forEach((item, index) => {
    const [x, y] = positions[index];
    const alpha = reveal(progress, index + 1, 4);
    drawLoop(ctx, x, y, 112, item, alpha);
    drawArrow(ctx, 575, 550, x - 120, y, { label: item.relation, stroke: color("practitioner"), alpha });
  });
  drawCard(ctx, 1320, 770, 430, 74, { label: visual.returnLabel, role: "static", titleSize: 19 }, reveal(progress, 3, 4));
}

function renderAccess(ctx, slide, progress) {
  const visual = slide.visual;
  visual.loops.forEach((item, index) => {
    const y = 420 + index * 200;
    drawLoop(ctx, 370, y, 90, item, reveal(progress, index, 4));
    drawArrow(ctx, 464, y, 790, 555, { stroke: roleStyle(item.role).color, alpha: reveal(progress, index, 4) });
  });
  drawCard(ctx, 790, 300, 1030, 550, { label: visual.context.label, role: "static", items: visual.context.items, titleSize: 32 }, reveal(progress, 3, 4));
}

function renderPillars(ctx, slide, progress) {
  slide.visual.pillars.forEach((pillar, index) => {
    drawCard(ctx, 100 + index * 435, 320, 400, 470, { ...pillar, titleSize: 29 }, reveal(progress, index, 4));
    drawLoop(ctx, 300 + index * 435, 700, 62, { label: pillar.label, role: pillar.role }, reveal(progress, index, 4));
  });
}

function renderIntelligenceBranch(ctx, slide, progress) {
  const visual = slide.visual;
  drawLoop(ctx, 390, 550, 155, { label: visual.branch, role: visual.role }, reveal(progress, 0, 3));
  drawCard(ctx, 690, 300, 500, 520, { label: visual.operations[0], role: visual.role, items: visual.operations.slice(1), titleSize: 29 }, reveal(progress, 1, 3));
  drawCard(ctx, 1240, 300, 580, 520, { label: visual.items[0], role: "static", items: visual.items.slice(1), titleSize: 27 }, reveal(progress, 2, 3));
  drawArrow(ctx, 550, 550, 690, 550, { stroke: color("intelligence"), alpha: reveal(progress, 1, 3) });
  drawArrow(ctx, 1190, 550, 1240, 550, { stroke: color("intelligence"), alpha: reveal(progress, 2, 3) });
}

function renderMatrix(ctx, slide, progress) {
  const visual = slide.visual;
  const x = 100;
  const y = 315;
  const labelWidth = 190;
  const cellWidth = 302;
  const headerHeight = 74;
  const rowHeight = 145;
  drawCard(ctx, x, y, labelWidth, headerHeight, { label: visual.status[0], role: "static", titleSize: 18 }, 1);
  visual.columns.forEach((column, index) => {
    roundedRect(ctx, x + labelWidth + index * cellWidth, y, cellWidth, headerHeight, 0, color("solutionSoft"), color("line"), 1);
    drawText(ctx, column, x + labelWidth + index * cellWidth + cellWidth / 2, y + 24, { size: 20, weight: 750, align: "center", maxWidth: cellWidth - 30, maxLines: 1 });
  });
  visual.rows.forEach((row, rowIndex) => {
    const rowY = y + headerHeight + rowIndex * rowHeight;
    const alpha = reveal(progress, rowIndex, visual.rows.length);
    roundedRect(ctx, x, rowY, labelWidth, rowHeight, 0, color("staticSoft"), color("line"), 1);
    drawText(ctx, row.label, x + 22, rowY + 52, { size: 20, weight: 760, maxWidth: labelWidth - 40, maxLines: 2 });
    row.cells.forEach((cell, cellIndex) => {
      const cellX = x + labelWidth + cellIndex * cellWidth;
      roundedRect(ctx, cellX, rowY, cellWidth, rowHeight, 0, color("paper"), color("line"), 1);
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color("solution");
      ctx.beginPath();
      ctx.arc(cellX + 33, rowY + rowHeight / 2, 12, 0, FULL_CIRCLE);
      ctx.fill();
      drawText(ctx, cell, cellX + 58, rowY + 52, { size: 19, weight: 600, maxWidth: cellWidth - 82, maxLines: 2 });
      ctx.restore();
    });
  });
}

function renderDag(ctx, slide, progress) {
  const visual = slide.visual;
  const vertexById = new Map();
  visual.vertices.forEach((vertex) => {
    vertexById.set(vertex.id, { ...vertex, canvasY: vertex.y + 140 });
  });
  visual.edges.forEach((edge, index) => {
    const from = vertexById.get(edge.from);
    const to = vertexById.get(edge.to);
    drawArrow(ctx, from.x + 82, from.canvasY, to.x - 82, to.canvasY, { label: edge.label, stroke: roleStyle(to.role).color, alpha: reveal(progress, index, visual.edges.length + visual.vertices.length) });
  });
  visual.vertices.forEach((vertex, index) => {
    const point = vertexById.get(vertex.id);
    drawLoop(ctx, point.x, point.canvasY, 80, vertex, reveal(progress, visual.edges.length + index, visual.edges.length + visual.vertices.length));
  });
  if (visual.terminal) {
    const from = vertexById.get(visual.terminal.from);
    const terminalX = 1740;
    const terminalY = from.canvasY;
    const alpha = reveal(progress, visual.edges.length + visual.vertices.length, visual.edges.length + visual.vertices.length + 1);
    drawArrow(ctx, from.x + 82, from.canvasY, terminalX - 125, terminalY, { stroke: color("solution"), alpha });
    drawCard(ctx, terminalX - 120, terminalY - 62, 210, 124, { label: visual.terminal.label, tag: visual.terminal.type, role: "static", titleSize: 18 }, alpha);
  }
}

function renderServices(ctx, slide, progress) {
  const visual = slide.visual;
  drawLoop(ctx, 960, 440, 132, visual.center, reveal(progress, 0, 4));
  const positions = [
    [110, 650], [760, 650], [1410, 650]
  ];
  visual.groups.forEach((group, index) => {
    const [x, y] = positions[index];
    const alpha = reveal(progress, index + 1, 4);
    drawCard(ctx, x, y, 400, 125, { label: group, role: "static", titleSize: 20 }, alpha);
    drawArrow(ctx, 960, 575, x + 200, y, { stroke: color("static"), alpha });
  });
}

function renderWorkflow(ctx, slide, progress) {
  const steps = slide.visual.steps;
  steps.forEach((step, index) => {
    const row = index < 4 ? 0 : 1;
    const column = index % 4;
    const x = 250 + column * 460;
    const y = row === 0 ? 430 : 740;
    const alpha = reveal(progress, index, steps.length);
    drawLoop(ctx, x, y, 88, step, alpha);
    if (column < 3) drawArrow(ctx, x + 92, y, x + 368, y, { stroke: roleStyle(step.role).color, alpha });
    if (index === 3) drawArrow(ctx, x, y + 92, x, 648, { stroke: color("static"), alpha });
  });
}

function renderWorkedStage(ctx, slide, progress) {
  const visual = slide.visual;
  visual.loops.forEach((item, index) => {
    const x = 230 + index * 450;
    const y = 450;
    const alpha = reveal(progress, index, visual.loops.length + 1);
    drawLoop(ctx, x, y, 96, item, alpha);
    if (index < visual.loops.length - 1) drawArrow(ctx, x + 100, y, x + 350, y, { stroke: roleStyle(item.role).color, alpha });
  });
  drawCard(ctx, 100, 630, 1720, 245, { label: visual.questionsLabel, role: "intelligence", items: visual.questions, titleSize: 24 }, reveal(progress, visual.loops.length, visual.loops.length + 1));
}

function renderVerifyCompile(ctx, slide, progress) {
  const visual = slide.visual;
  drawCard(ctx, 100, 430, 320, 140, { ...visual.candidate, role: "static", titleSize: 23 }, reveal(progress, 0, 5));
  drawLoop(ctx, 650, 500, 110, visual.verifier, reveal(progress, 1, 5));
  drawCard(ctx, 970, 290, 300, 140, { ...visual.accepted, titleSize: 23 }, reveal(progress, 2, 5));
  drawLoop(ctx, 1100, 680, 105, visual.repair, reveal(progress, 3, 5));
  drawArrow(ctx, 420, 500, 535, 500, { stroke: color("practitioner"), alpha: reveal(progress, 1, 5) });
  drawArrow(ctx, 765, 470, 970, 360, { label: visual.accepted.relation, stroke: color("accepted"), alpha: reveal(progress, 2, 5) });
  drawArrow(ctx, 765, 530, 990, 650, { label: visual.repair.relation, stroke: color("danger"), alpha: reveal(progress, 3, 5) });
  drawArrow(ctx, 1010, 680, 700, 585, { dashed: true, stroke: color("improvement"), alpha: reveal(progress, 3, 5) });
  drawCard(ctx, 1330, 300, 490, 520, { label: visual.runHistory.label, role: "static", items: visual.runHistory.items, titleSize: 32 }, reveal(progress, 4, 5));
}

function renderFinal(ctx, slide, progress) {
  const visual = slide.visual;
  drawCard(ctx, 100, 270, 800, 470, { label: "Practitioner task profiles", role: "practitioner", items: visual.practitionerTasks, titleSize: 30 }, reveal(progress, 0, 4));
  drawCard(ctx, 190, 770, 620, 95, { label: visual.reviewLabel, role: "static", titleSize: 20 }, reveal(progress, 1, 4));
  visual.statements.forEach((statement, index) => {
    drawCard(ctx, 970, 300 + index * 175, 850, 145, { label: statement, role: ["practitioner", "intelligence", "solution"][index], titleSize: 24 }, reveal(progress, index + 1, 4));
  });
}

const renderers = {
  title: renderTitle,
  overview: renderOverview,
  "loop-object": renderLoopObject,
  "typed-flow": renderTypedFlow,
  "two-column": renderTwoColumn,
  mode: renderMode,
  comparison: renderComparison,
  hierarchy: renderHierarchy,
  steps: renderSteps,
  spawn: renderSpawn,
  access: renderAccess,
  pillars: renderPillars,
  "intelligence-branch": renderIntelligenceBranch,
  matrix: renderMatrix,
  dag: renderDag,
  services: renderServices,
  workflow: renderWorkflow,
  "worked-stage": renderWorkedStage,
  "verify-compile": renderVerifyCompile,
  final: renderFinal
};

export function renderSlide(index, ctx, progress = 1) {
  const safeIndex = Math.max(0, Math.min(timelineSlides.length - 1, index));
  const slide = timelineSlides[safeIndex];
  const canvas = ctx.canvas;
  canvas.width = showcaseData.meta.width;
  canvas.height = showcaseData.meta.height;
  ctx.save();
  ctx.fillStyle = color("background");
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  drawHeader(ctx, slide);
  const renderer = renderers[slide.kind];
  if (renderer) renderer(ctx, slide, Math.max(0, Math.min(1, progress)));
  drawAnnotationAndFooter(ctx, slide, safeIndex);
  ctx.restore();
  return slide;
}

export function slideAtTime(timeMs) {
  const bounded = Math.max(0, Math.min(durationMs - 1, Number(timeMs) || 0));
  return timelineSlides.find((slide) => bounded >= slide.startMs && bounded < slide.endMs) || timelineSlides[timelineSlides.length - 1];
}

export function renderFrame(timeMs, ctx) {
  const slide = slideAtTime(timeMs);
  const progress = slide.durationMs ? (timeMs - slide.startMs) / slide.durationMs : 1;
  renderSlide(slide.index, ctx, progress);
  return slide;
}

export { showcaseData };
