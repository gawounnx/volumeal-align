const allowed=new Set(['image/jpeg','image/png','image/webp']);
const brands=new Set(['heic','heix','hevc','hevx','heim','heis','mif1','msf1']);
export type FileValidationResult={valid:true}|{valid:false;code:'EMPTY'|'TOO_LARGE'|'HEIC_UNSUPPORTED'|'UNSUPPORTED_TYPE';message:string};
async function isHeic(file:Blob){const b=new Uint8Array(await file.slice(0,12).arrayBuffer());return b.length>=12&&String.fromCharCode(...b.slice(4,8))==='ftyp'&&brands.has(String.fromCharCode(...b.slice(8,12)).toLowerCase())}
// Ref: BR-VAL-003. Check both extension and ISO BMFF brand.
export async function validateImageFile(file:File):Promise<FileValidationResult>{if(!file.size)return {valid:false,code:'EMPTY',message:'0바이트보다 큰 이미지를 선택해 주세요.'};if(file.size>10*1024*1024)return {valid:false,code:'TOO_LARGE',message:'10MB 이하 이미지를 선택해 주세요.'};if(/\.(heic|heif)$/i.test(file.name)||await isHeic(file))return {valid:false,code:'HEIC_UNSUPPORTED',message:'HEIC 형식은 지원하지 않습니다. JPEG로 변환 후 업로드해 주세요.'};if(!allowed.has(file.type))return {valid:false,code:'UNSUPPORTED_TYPE',message:'JPEG, PNG, WebP 형식의 이미지를 선택해 주세요.'};return {valid:true}}
