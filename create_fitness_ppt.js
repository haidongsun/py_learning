const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

const { FaDumbbell, FaRunning, FaHeartbeat, FaBullseye, FaShieldAlt, FaHome, FaMoneyBillWave, FaStar, FaFire, FaChartLine, FaCheckCircle, FaLightbulb, FaTools, FaCouch, FaBicycle, FaWater } = require("react-icons/fa");

// ── Color Palette ──
const C = {
  bg:       "0B1120",
  cardBg:   "1A2235",
  orange:   "FF6B35",
  cyan:     "00D4AA",
  white:    "FFFFFF",
  text:     "E2E8F0",
  muted:    "64748B",
  cardBorder:"2D3748",
};

// ── Icon helper ──
async function icon(IconComponent, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color: "#" + color, size: String(size) })
  );
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

// ── Reusable layout helpers ──
const SLIDE_W = 10, SLIDE_H = 5.625;
const MARGIN = 0.6;

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Fitness Guide";
  pres.title = "健身器材完全指南";

  // ── Slide 1: Title ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };

    // Large accent shape behind title
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 5.625,
      fill: { color: C.bg }
    });
    // Decorative corner accent shape
    slide.addShape(pres.shapes.RECTANGLE, {
      x: -1, y: 0.3, w: 3.5, h: 0.06,
      fill: { color: C.orange }, rotate: -18
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: -1, y: 0.8, w: 2.5, h: 0.04,
      fill: { color: C.cyan }, rotate: -18
    });

    // Dumbbell icon
    const dumbbellIcon = await icon(FaDumbbell, C.orange, 256);
    slide.addImage({ data: dumbbellIcon, x: 4.35, y: 1.35, w: 1.3, h: 1.3 });

    slide.addText("健身器材完全指南", {
      x: 0.5, y: 2.7, w: 9, h: 1.2,
      fontSize: 42, fontFace: "Arial Black", color: C.white,
      bold: true, align: "center", valign: "middle", margin: 0
    });
    slide.addText("从入门到精通 · 科学选择你的专属健身装备", {
      x: 1, y: 3.9, w: 8, h: 0.6,
      fontSize: 16, fontFace: "Calibri", color: C.muted,
      align: "center", valign: "middle"
    });

    // Bottom stats bar
    const statsY = 4.35;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: statsY, w: 10, h: 1.275,
      fill: { color: C.cardBg }
    });
    const stats = [
      { num: "4", label: "有氧器材" },
      { num: "4", label: "力量器材" },
      { num: "3", label: "选购维度" },
      { num: "4", label: "安全守则" },
    ];
    const statW = 9 / 4;
    stats.forEach((s, i) => {
      const sx = 0.5 + i * statW;
      slide.addText(s.num, {
        x: sx, y: statsY + 0.15, w: statW, h: 0.5,
        fontSize: 28, fontFace: "Arial Black", color: C.orange,
        bold: true, align: "center", valign: "middle", margin: 0
      });
      slide.addText(s.label, {
        x: sx, y: statsY + 0.65, w: statW, h: 0.35,
        fontSize: 12, fontFace: "Calibri", color: C.muted,
        align: "center", valign: "middle", margin: 0
      });
    });
  }

  // ── Slide 2: 有氧器材 2x2 Grid ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };
    addSectionTitle(slide, pres, "有氧器材概览", "燃脂 · 心肺 · 耐力");

    const icons_cardio = [
      await icon(FaRunning, C.orange),
      await icon(FaHeartbeat, C.orange),
      await icon(FaWater, C.orange),
      await icon(FaBicycle, C.orange),
    ];

    const cardioItems = [
      { name: "跑步机", desc: "经典减脂利器\n模拟户外跑步体验", tag: "燃脂首选" },
      { name: "椭圆机", desc: "低冲击有氧运动\n保护膝盖与关节", tag: "关节友好" },
      { name: "划船机", desc: "调动全身 80% 肌群\n有氧与力量兼得", tag: "全身运动" },
      { name: "动感单车", desc: "高燃脂率有氧\n节奏感强释放压力", tag: "高效燃脂" },
    ];

    render2x2Grid(slide, pres, cardioItems, icons_cardio, C.orange);
  }

  // ── Slide 3: 力量器材 2x2 Grid ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };
    addSectionTitle(slide, pres, "力量器材概览", "增肌 · 塑形 · 力量");

    const icons_strength = [
      await icon(FaDumbbell, C.cyan),
      await icon(FaDumbbell, C.cyan),
      await icon(FaCouch, C.cyan),
      await icon(FaDumbbell, C.cyan),
    ];

    const strengthItems = [
      { name: "哑铃", desc: "最基础的自由力量\n适合各类孤立训练", tag: "自由力量" },
      { name: "杠铃", desc: "大重量复合动作首选\n深蹲硬拉卧推核心", tag: "复合动作" },
      { name: "综合训练器", desc: "一机多用安全可靠\n适合家庭健身房", tag: "安全全面" },
      { name: "弹力带", desc: "轻便易携随处可练\n热身康复首选工具", tag: "便携灵活" },
    ];

    render2x2Grid(slide, pres, strengthItems, icons_strength, C.cyan);
  }

  // ── Slide 4: 按目标选择 ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };
    addSectionTitle(slide, pres, "按健身目标选择器材", "不同目标，不同装备配置");

    const goals = [
      { goal: "减脂", icon_data: await icon(FaFire, C.orange), eq: "跑步机 / 动感单车 / 划船机", tip: "优先有氧器材，保持心率 60-80% 最大心率" },
      { goal: "增肌", icon_data: await icon(FaDumbbell, C.orange), eq: "哑铃 / 杠铃 / 综合训练器", tip: "大重量低次数，渐进超负荷原则" },
      { goal: "塑形", icon_data: await icon(FaStar, C.orange), eq: "弹力带 / 瑜伽垫 / TRX", tip: "中重量多次数，注重肌肉感受度" },
      { goal: "康复", icon_data: await icon(FaShieldAlt, C.orange), eq: "弹力带 / 椭圆机", tip: "低强度低冲击，听从医嘱逐步恢复" },
    ];

    const cardW = 2.0;
    const cardH = 2.2;
    const gap = 0.18;
    const startX = (10 - (cardW * 4 + gap * 3)) / 2; // ~0.77

    goals.forEach((g, i) => {
      const cx = startX + i * (cardW + gap);
      const cy = 1.7;

      // Card
      slide.addShape(pres.shapes.RECTANGLE, {
        x: cx, y: cy, w: cardW, h: cardH,
        fill: { color: C.cardBg },
        shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.2 }
      });

      // Icon
      slide.addImage({ data: g.icon_data, x: cx + cardW / 2 - 0.3, y: cy + 0.15, w: 0.6, h: 0.6 });

      // Goal name
      slide.addText(g.goal, {
        x: cx, y: cy + 0.85, w: cardW, h: 0.4,
        fontSize: 18, fontFace: "Calibri", color: C.white, bold: true,
        align: "center", valign: "middle", margin: 0
      });

      // Equipment
      slide.addText(g.eq, {
        x: cx + 0.15, y: cy + 1.25, w: cardW - 0.3, h: 0.35,
        fontSize: 11, fontFace: "Calibri", color: C.orange,
        align: "center", valign: "middle", margin: 0
      });

      // Tip
      slide.addText(g.tip, {
        x: cx + 0.15, y: cy + 1.6, w: cardW - 0.3, h: 0.45,
        fontSize: 10, fontFace: "Calibri", color: C.muted,
        align: "center", valign: "middle", margin: 0
      });
    });
  }

  // ── Slide 5: 有氧器材对比表格 ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };
    addSectionTitle(slide, pres, "有氧器材横向对比", "多维度评估，找到最适合你的器械");

    const headerOpts = { fill: { color: C.orange }, color: C.white, bold: true, fontSize: 12, fontFace: "Calibri", align: "center", valign: "middle" };
    const cellOpts = { fill: { color: C.cardBg }, color: C.text, fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle", border: { pt: 0.5, color: C.cardBorder } };

    const tableData = [
      [
        { text: "器材", options: headerOpts },
        { text: "燃脂效率", options: headerOpts },
        { text: "关节冲击", options: headerOpts },
        { text: "空间需求", options: headerOpts },
        { text: "价格区间", options: headerOpts },
      ],
      [
        { text: "跑步机", options: { ...cellOpts, bold: true, color: C.orange } },
        { text: "⭐⭐⭐⭐⭐", options: cellOpts },
        { text: "中等", options: cellOpts },
        { text: "较大", options: cellOpts },
        { text: "¥2000-20000", options: cellOpts },
      ],
      [
        { text: "椭圆机", options: { ...cellOpts, bold: true, color: C.orange } },
        { text: "⭐⭐⭐⭐", options: cellOpts },
        { text: "低", options: cellOpts },
        { text: "中等", options: cellOpts },
        { text: "¥1500-15000", options: cellOpts },
      ],
      [
        { text: "划船机", options: { ...cellOpts, bold: true, color: C.orange } },
        { text: "⭐⭐⭐⭐⭐", options: cellOpts },
        { text: "极低", options: cellOpts },
        { text: "中等(可折叠)", options: cellOpts },
        { text: "¥1000-12000", options: cellOpts },
      ],
      [
        { text: "动感单车", options: { ...cellOpts, bold: true, color: C.orange } },
        { text: "⭐⭐⭐⭐", options: cellOpts },
        { text: "低", options: cellOpts },
        { text: "较小", options: cellOpts },
        { text: "¥800-8000", options: cellOpts },
      ],
    ];

    slide.addTable(tableData, {
      x: 0.6, y: 1.7, w: 8.8,
      colW: [1.8, 1.6, 1.6, 2.0, 1.8],
      border: { pt: 0.5, color: C.cardBorder },
      rowH: [0.45, 0.55, 0.55, 0.55, 0.55],
    });
  }

  // ── Slide 6: 选购建议 ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };
    addSectionTitle(slide, pres, "器材选购指南", "四大维度帮你做出明智决策");

    const tips = [
      { icon_data: await icon(FaHome, C.cyan), title: "空间考量", desc: "测量预留区域，跑步机需 2m×1m，折叠机型可节省空间。划船机和动感单车占地最小。" },
      { icon_data: await icon(FaMoneyBillWave, C.cyan), title: "预算分配", desc: "入门级 2-5K，中端 5-15K，高端 15K+。建议核心器材投入最多，配件次之。" },
      { icon_data: await icon(FaStar, C.cyan), title: "品质优先", desc: "检查电机功率、承重上限、材质工艺。知名品牌售后更有保障，避免贪便宜买劣质产品。" },
      { icon_data: await icon(FaCheckCircle, C.cyan), title: "亲身试用", desc: "不同品牌手感差异大，建议到实体店试用后再决定。关注噪音、平稳度和操作便捷性。" },
    ];

    renderIconRows(slide, pres, tips, C.cyan);
  }

  // ── Slide 7: 安全使用指南 ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };
    addSectionTitle(slide, pres, "安全使用指南", "科学训练 · 远离伤病");

    const tips = [
      { icon_data: await icon(FaFire, C.orange), title: "充分热身", desc: "训练前进行 5-10 分钟动态热身，提升心率，激活目标肌群，预防拉伤。" },
      { icon_data: await icon(FaBullseye, C.orange), title: "正确姿势", desc: "学习标准动作要领，避免代偿发力。初学者建议在教练指导下掌握基础动作模式。" },
      { icon_data: await icon(FaChartLine, C.orange), title: "循序渐进", desc: "每周增加不超过 10% 的训练量。听从身体反馈，疲劳时及时调整或休息。" },
      { icon_data: await icon(FaTools, C.orange), title: "定期维护", desc: "检查螺丝松紧、跑带偏移、线缆磨损。每月进行一次全面检查，确保设备安全可靠。" },
    ];

    renderIconRows(slide, pres, tips, C.orange);
  }

  // ── Slide 8: 总结 ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.bg };

    // Decorative top bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.06,
      fill: { color: C.orange }
    });

    // Large center content
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 1.5, y: 0.8, w: 7, h: 3.8,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 15, offset: 5, angle: 135, opacity: 0.25 }
    });

    const lightbulbIcon = await icon(FaLightbulb, C.orange, 256);
    slide.addImage({ data: lightbulbIcon, x: 4.4, y: 1.0, w: 1.2, h: 1.2 });

    slide.addText("选择适合自己的，坚持比器材更重要", {
      x: 1.8, y: 2.3, w: 6.4, h: 0.7,
      fontSize: 22, fontFace: "Calibri", color: C.white, bold: true,
      align: "center", valign: "middle", margin: 0
    });

    slide.addText("没有最好的器材，只有最合适的搭配\n了解自己的身体，明确训练目标，量力而行", {
      x: 1.8, y: 3.0, w: 6.4, h: 0.7,
      fontSize: 13, fontFace: "Calibri", color: C.muted,
      align: "center", valign: "middle", margin: 0
    });

    // Orange accent line
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 3.5, y: 3.8, w: 3, h: 0.04,
      fill: { color: C.orange }
    });

    slide.addText("现在就开始你的健身之旅", {
      x: 1.8, y: 4.0, w: 6.4, h: 0.5,
      fontSize: 16, fontFace: "Calibri", color: C.orange, bold: true,
      align: "center", valign: "middle", margin: 0
    });
  }

  // ── Write File ──
  await pres.writeFile({ fileName: "健身器材指南.pptx" });
  console.log("✅ 演示文稿已生成: 健身器材指南.pptx");
}

// ── Helpers ──

function addSectionTitle(slide, pres, title, subtitle) {
  slide.addText(title, {
    x: MARGIN, y: 0.3, w: 9, h: 0.7,
    fontSize: 30, fontFace: "Calibri", color: C.white, bold: true,
    align: "left", valign: "middle", margin: 0
  });
  slide.addText(subtitle, {
    x: MARGIN, y: 0.95, w: 9, h: 0.35,
    fontSize: 13, fontFace: "Calibri", color: C.muted,
    align: "left", valign: "middle", margin: 0
  });
  // Subtle separator line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: MARGIN, y: 1.35, w: 2, h: 0.03,
    fill: { color: C.orange }
  });
}

function render2x2Grid(slide, pres, items, iconsData, accentColor) {
  const cardW = 4.05;
  const cardH = 1.45;
  const gapX = 0.3;
  const gapY = 0.2;
  const startX = (10 - (cardW * 2 + gapX)) / 2; // ~0.8
  const startY = 1.55;

  for (let i = 0; i < 4; i++) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const cx = startX + col * (cardW + gapX);
    const cy = startY + row * (cardH + gapY);
    const item = items[i];

    // Card background
    slide.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: cardW, h: cardH,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.15 }
    });

    // Left accent bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: 0.06, h: cardH,
      fill: { color: accentColor }
    });

    // Icon
    slide.addImage({ data: iconsData[i], x: cx + 0.25, y: cy + 0.3, w: 0.65, h: 0.65 });

    // Name
    slide.addText(item.name, {
      x: cx + 1.05, y: cy + 0.2, w: 2.5, h: 0.45,
      fontSize: 18, fontFace: "Calibri", color: C.white, bold: true,
      align: "left", valign: "middle", margin: 0
    });

    // Description
    slide.addText(item.desc, {
      x: cx + 1.05, y: cy + 0.65, w: 2.5, h: 0.6,
      fontSize: 11, fontFace: "Calibri", color: C.muted,
      align: "left", valign: "top", margin: 0
    });

    // Tag pill
    const tagW = 0.85;
    const tagH = 0.28;
    const tagX = cx + cardW - tagW - 0.25;
    const tagY = cy + cardH - tagH - 0.15;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: tagX, y: tagY, w: tagW, h: tagH,
      fill: { color: accentColor, transparency: 85 },
      rectRadius: 0.05
    });
    slide.addText(item.tag, {
      x: tagX, y: tagY, w: tagW, h: tagH,
      fontSize: 9, fontFace: "Calibri", color: accentColor, bold: true,
      align: "center", valign: "middle", margin: 0
    });
  }
}

function renderIconRows(slide, pres, items, accentColor) {
  const rowH = 0.82;
  const gap = 0.14;
  const startY = 1.55;
  const iconSize = 0.55;

  items.forEach((item, i) => {
    const ry = startY + i * (rowH + gap);

    // Row background
    slide.addShape(pres.shapes.RECTANGLE, {
      x: MARGIN, y: ry, w: 8.8, h: rowH,
      fill: { color: C.cardBg },
      shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.1 }
    });

    // Left accent bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: MARGIN, y: ry, w: 0.06, h: rowH,
      fill: { color: accentColor }
    });

    // Icon circle
    const circleX = MARGIN + 0.35;
    const circleY = ry + (rowH - iconSize) / 2;
    slide.addShape(pres.shapes.OVAL, {
      x: circleX - 0.02, y: circleY - 0.02, w: iconSize + 0.04, h: iconSize + 0.04,
      fill: { color: accentColor, transparency: 85 }
    });
    slide.addImage({ data: item.icon_data, x: circleX, y: circleY, w: iconSize, h: iconSize });

    // Title
    slide.addText(item.title, {
      x: MARGIN + 1.1, y: ry + 0.08, w: 2.2, h: 0.35,
      fontSize: 15, fontFace: "Calibri", color: C.white, bold: true,
      align: "left", valign: "middle", margin: 0
    });

    // Description
    slide.addText(item.desc, {
      x: MARGIN + 1.1, y: ry + 0.42, w: 7.3, h: 0.38,
      fontSize: 11, fontFace: "Calibri", color: C.muted,
      align: "left", valign: "middle", margin: 0
    });
  });
}

main().catch(err => { console.error(err); process.exit(1); });
