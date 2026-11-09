import { http, HttpResponse } from 'msw'
import { API } from '../respond'

// 429 확인용 임시 시나리오 (개발 mock 전용). 브라우저 콘솔에서 켜고 끈다
//   sessionStorage.setItem('mock429', 'html')   nginx 기본 HTML 본문
//   sessionStorage.setItem('mock429', 'json')   JSON 본문 + message
//   sessionStorage.setItem('mock429', 'empty')  JSON 본문, message 없음
//   sessionStorage.removeItem('mock429')        끄기
// 재발급(/auth/refresh)은 제외 (새로고침 시 로그아웃되지 않게)
const HTML = '<html>\r\n<head><title>429 Too Many Requests</title></head>\r\n<body>\r\n<center><h1>429 Too Many Requests</h1></center>\r\n<hr><center>nginx</center>\r\n</body>\r\n</html>\r\n'

function mode() {
  try {
    return sessionStorage.getItem('mock429')
  } catch {
    return null
  }
}

export const rateLimitHandlers = [
  http.all(`${API}/*`, ({ request }) => {
    const m = mode()
    if (!m || new URL(request.url).pathname.endsWith('/auth/refresh')) return
    if (m === 'html') return new HttpResponse(HTML, { status: 429, headers: { 'Content-Type': 'text/html' } })
    const body = { success: false, data: null, code: 'TOO_MANY_REQUESTS' }
    return HttpResponse.json(m === 'empty' ? body : { ...body, message: '[mock] 서버 429 메시지' }, { status: 429 })
  }),
]
