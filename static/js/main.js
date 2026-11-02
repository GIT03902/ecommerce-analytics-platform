// ============ ECharts 通用配置 ============
const CHART_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#0891b2', '#7c3aed', '#db2777', '#65a30d', '#0d9488', '#ea580c'];

// 浅色主题基础配置
const BASE_OPTION = {
  textStyle: {
    fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
    color: '#1e293b'
  },
  color: CHART_COLORS
};

// ============ 工具函数 ============
function fmtMoney(n) {
  n = Number(n);
  if (n >= 1e8) return (n / 1e8).toFixed(2) + ' 亿';
  if (n >= 1e4) return (n / 1e4).toFixed(2) + ' 万';
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function fmtMoneyYuan(n) {
  return '¥' + fmtMoney(n);
}

function fmtNum(n) {
  return Number(n).toLocaleString();
}

// ============ 中国地图注册 ============
function registerChinaMap(callback) {
  if (window._chinaMapRegistered) { callback(); return; }
  fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json')
    .then(r => r.json())
    .then(geo => {
      echarts.registerMap('china', geo);
      window._chinaMapRegistered = true;
      callback();
    })
    .catch(err => {
      console.warn('中国地图加载失败：', err);
      callback();
    });
}

// ============ 通用图表初始化辅助 ============
function makeChart(domId, option) {
  const dom = document.getElementById(domId);
  if (!dom) return null;
  const chart = echarts.init(dom);
  const merged = Object.assign({}, BASE_OPTION, option);
  merged.textStyle = Object.assign({}, BASE_OPTION.textStyle, option.textStyle || {});
  chart.setOption(merged);
  window.addEventListener('resize', () => chart.resize());
  return chart;
}

// tooltip 通用样式
const TOOLTIP_STYLE = {
  backgroundColor: 'rgba(30,41,59,0.92)',
  borderWidth: 0,
  textStyle: { color: '#f8fafc', fontSize: 13 }
};
