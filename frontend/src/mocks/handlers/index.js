import { authHandlers } from './auth'
import { chatHandlers } from './chats'

// 다음 단계: documentHandlers 를 handlers/ 에 추가하고 여기에 펼친다
export const handlers = [...authHandlers, ...chatHandlers]
