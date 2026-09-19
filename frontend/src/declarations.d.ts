// 전역 CSS 및 정적 자산에 대한 TypeScript 모듈 선언 [ts(2882) 방지]
declare module "*.css" {
  const content: { [className: string]: string };
  export default content;
}
