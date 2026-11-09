import { authHandlers } from './auth'
import { chatHandlers } from './chats'
import { documentHandlers } from './documents'
import { rateLimitHandlers } from './rateLimit'

export const handlers = [...rateLimitHandlers, ...authHandlers, ...chatHandlers, ...documentHandlers]
