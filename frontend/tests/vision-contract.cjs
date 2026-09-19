// Contract smoke test using the specification fixture; WebGL is stubbed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const fixture = require('./fixtures/vision-estimate.json');

function load(relativePath, overrides = {}, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
  }}).outputText;
  const exports = {};
  vm.runInNewContext(code, {
    exports, require: name => overrides[name] ?? require(name), process,
    ...globals,
  });
  return exports;
}

function renderResult(result) {
  let stateIndex = 0;
  const effects = [];
  const boxes = [];
  const context = { drawImage() {}, fillRect() {}, fillText() {},
    strokeRect: (...args) => boxes.push(args) };
  const canvas = { getContext: () => context };
  const hooks = { ...React,
    useState: initial => [stateIndex++ === 3 ? result : initial, () => {}],
    useRef: () => ({ current: canvas }),
    useEffect: effect => effects.push(effect),
  };
  // Supply a preview URL so the overlay effect also runs.
  const useState = hooks.useState;
  hooks.useState = initial => stateIndex === 1
    ? (stateIndex++, ['blob:test', () => {}]) : useState(initial);
  const Page = load('src/app/page.tsx', {
    react: { ...hooks, useCallback: callback => callback }, 'next/dynamic': () => () => null,
    '../components/MealHistory': () => null,
    '../services/api': { getServiceStatus: async () => '분석 데이터 준비 필요' },
    '../stores/useMealCorrectionStore': { correctFoodItemWeight: (item, weightG) => { const ratio = weightG / item.weightG; return { ...item, weightG, caloriesKcal: item.caloriesKcal * ratio, carbsG: item.carbsG * ratio, proteinG: item.proteinG * ratio, fatG: item.fatG * ratio, sodiumMg: item.sodiumMg * ratio }; } },
    '../utils/fileValidator': { validateImageFile: async () => ({ valid: true }) },
    '../components/modals/MealCorrectionModal': () => null,
    '../components/ui/Toast': () => null,
  }, { Image: class {
    naturalWidth = 640; naturalHeight = 480;
    set src(value) { this.onload?.(); }
  }}).default;
  const html = renderToStaticMarkup(React.createElement(Page));
  effects.forEach(effect => effect());
  return { html, boxes };
}

async function main() {
  const { html, boxes } = renderResult(fixture.data);
  assert.ok(html.includes('백미밥'));
  assert.ok(html.includes(fixture.data.drugWarnings[0].warningTitle));
  assert.ok(html.includes('320.5'));
  const bbox = fixture.data.foodItems[0].bbox2d;
  const expected = [bbox.xmin * 640, bbox.ymin * 480,
    (bbox.xmax - bbox.xmin) * 640, (bbox.ymax - bbox.ymin) * 480];
  boxes[0].forEach((value, index) => assert.ok(Math.abs(value - expected[index]) < 1e-8));
  const uncertainItem = { ...fixture.data.foodItems[0], requiresConfirmation: true };
  const uncertain = renderResult({ ...fixture.data, isPersisted: false, requiresConfirmation: true, foodItems: [uncertainItem] });
  assert.ok(uncertain.html.includes('후보에 정답 없음'));
  assert.ok(uncertain.html.includes('음식 확인 필요'));

  const empty = renderResult({ ...fixture.data, foodItems: [], drugWarnings: [] });
  assert.ok(empty.html.includes('이번 분석에서 반환된 상호작용 경고가 없습니다.'));
  assert.equal(empty.boxes.length, 0);
  assert.ok(renderResult(null).html.includes('식단 이미지 업로드'));
  assert.ok(renderResult(null).html.includes('total-caloriesKcal'));
  assert.ok(html.includes('542.5 kcal'));

  let request;
  const apiClient = {
    defaults: { headers: { common: {} } },
    request: async options => { request = options; return { data: fixture }; },
  };
  const api = load('src/services/api.ts', { '../lib/apiClient': { apiClient } }, { FormData });
  const response = await api.estimateMealVision(new Blob(['test'], { type: 'image/jpeg' }));
  assert.equal(response.data.foodItems[0].foodName, '백미밥');
  assert.equal(request.url, '/vision/estimate');
  assert.equal(request.method, 'POST');
  assert.ok(request.data.has('file'));
  const saved = await api.confirmMealVision({ ...fixture.data, foodItems: fixture.data.foodItems.map(item => ({ ...item, requiresConfirmation: false })) });
  assert.equal(request.url, '/vision/confirm');
  assert.equal(JSON.parse(request.data).confirmedItems[0].weightG, fixture.data.foodItems[0].weightG);
  assert.equal(saved.isPersisted, true);
  assert.equal(saved.requiresConfirmation, false);
  for (const [code, message] of [
    ['ERR_GEOMETRY_PLANE_NOT_FOUND', /다시 촬영/],
    ['ERR_ZERO_OBJECT_DETECTED', /실사진 학습 데이터 추가/],
  ]) {
    const failingClient = {
      defaults: { headers: { common: {} } },
      request: async () => { throw { response: { status: 422, data: { error: { code, message: 'original' } } } }; },
    };
    const failing = load('src/services/api.ts', { '../lib/apiClient': { apiClient: failingClient } }, { FormData });
    await assert.rejects(() => failing.estimateMealVision(new Blob(['test'])), message);
  }
  console.log('PASS: specification response, empty/initial states, 2D coordinates, API envelope');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
