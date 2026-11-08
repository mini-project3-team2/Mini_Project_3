import { authHandlers } from './auth'
import { chatHandlers } from './chats'
import { documentHandlers } from './documents'

export const handlers = [...authHandlers, ...chatHandlers, ...documentHandlers]
