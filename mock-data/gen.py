import json, os
from datetime import datetime, timedelta
B='mock-data'
def w(path, obj):
    p=os.path.join(B,path); os.makedirs(os.path.dirname(p),exist_ok=True)
    with open(p,'w',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n')
def wt(path, text):
    p=os.path.join(B,path); os.makedirs(os.path.dirname(p),exist_ok=True)
    with open(p,'w',encoding='utf-8',newline='\n') as f: f.write(text)
ok=lambda d,m="": {"success":True,"data":d,"message":m}
fail=lambda code,msg,data=None: {"success":False,"data":data,"message":msg,"code":code}

U={'student':'11111111-1111-4111-8111-111111111111','empty':'22222222-2222-4222-8222-222222222222',
   'indexing':'33333333-3333-4333-8333-333333333333','locked':'44444444-4444-4444-8444-444444444444',
   'other':'55555555-5555-4555-8555-555555555555','admin':'66666666-6666-4666-8666-666666666666'}
members=[
 {"id":1,"uuid":U['student'],"email":"student@test.com","password":"Test1234!","role":"MEMBER","failedLoginCount":0,"lockedUntil":None,"createdAt":"2026-11-07T10:00:00","_note":"기본 테스트 계정 — READY 자료 2개 + INDEXING 1개, 질문 기록 13건(10 · 3, 2페이지)"},
 {"id":2,"uuid":U['empty'],"email":"empty@test.com","password":"Test1234!","role":"MEMBER","failedLoginCount":0,"lockedUntil":None,"createdAt":"2026-11-07T10:05:00","_note":"자료 · 기록 없음 — 채팅 '자료 없음' 화면(3-2), 빈 목록 화면"},
 {"id":3,"uuid":U['indexing'],"email":"indexing@test.com","password":"Test1234!","role":"MEMBER","failedLoginCount":0,"lockedUntil":None,"createdAt":"2026-11-07T10:10:00","_note":"INDEXING 자료 1개만 — 질문 시 400 NO_DOCUMENT, '답변에 쓸 수 있는 자료가 아직 없어요'"},
 {"id":4,"uuid":U['locked'],"email":"locked@test.com","password":"Test1234!","role":"MEMBER","failedLoginCount":5,"lockedUntil":"2026-11-09T15:30:00","createdAt":"2026-11-07T10:15:00","_note":"로그인 5회 실패로 잠김 — 423 ACCOUNT_LOCKED"},
 {"id":5,"uuid":U['other'],"email":"other@test.com","password":"Test1234!","role":"MEMBER","failedLoginCount":0,"lockedUntil":None,"createdAt":"2026-11-07T10:20:00","_note":"다른 회원 — 자료 id 21 · 기록 id 201 소유. student로 접근하면 403 (IDOR 확인)"},
 {"id":6,"uuid":U['admin'],"email":"admin@test.com","password":"Admin1234!","role":"ADMIN","failedLoginCount":0,"lockedUntil":None,"createdAt":"2026-11-07T09:00:00","_note":"ADMIN — 화면 없음, Actuator 접근 확인용 (실제로는 환경 변수로 생성)"},
]
w('data/members.json',members)

docs=[
 {"id":1,"memberId":1,"originalFilename":"LangChain_RAG_실습.pdf","fileSize":2483112,"status":"READY","createdAt":"2026-11-07T11:00:00"},
 {"id":2,"memberId":1,"originalFilename":"Spring_Security_JWT.pdf","fileSize":3245890,"status":"READY","createdAt":"2026-11-07T11:20:00"},
 {"id":3,"memberId":1,"originalFilename":"Docker_Compose_정리.pdf","fileSize":1820334,"status":"INDEXING","createdAt":"2026-11-09T09:58:00"},
 {"id":11,"memberId":3,"originalFilename":"React_상태관리.pdf","fileSize":1503221,"status":"INDEXING","createdAt":"2026-11-09T10:01:00"},
 {"id":21,"memberId":5,"originalFilename":"다른회원_자료.pdf","fileSize":980112,"status":"READY","createdAt":"2026-11-08T14:00:00"},
]
w('data/documents.json',docs)
def pub_doc(d): return {k:d[k] for k in ["id","originalFilename","fileSize","status","createdAt"]}

S1=lambda p:{"documentId":1,"documentName":"LangChain_RAG_실습.pdf","page":p}
S2=lambda p:{"documentId":2,"documentName":"Spring_Security_JWT.pdf","page":p}
qa=[
 ("RAG에서 retriever의 similarity와 mmr 검색은 뭐가 달라?","similarity는 질문과 가장 비슷한 문서를 점수 순서대로 k개 가져오는 방식이에요. mmr은 비슷한 정도에 더해 이미 고른 문서와 겹치지 않는 정도도 함께 따져서, 다양한 내용을 골고루 가져와요.",[S1(12),S1(14)],"HELPFUL"),
 ("JWT에서 Refresh Token은 왜 DB에 해시로 저장해?","토큰 원문이 DB에 그대로 있으면 DB가 유출됐을 때 바로 도용될 수 있어요. 해시로 저장하면 원문을 알 수 없어서 피해를 줄일 수 있어요.",[S2(31)],None),
 ("청크 오버랩은 왜 필요해?","청크 경계에 걸린 문장이 잘려 의미를 잃지 않도록, 이웃한 청크끼리 일부를 겹쳐서 저장해요.",[S1(8)],"HELPFUL"),
 ("Refresh Token 회전은 어떻게 동작해?","재발급할 때마다 새 Refresh Token을 발급하고 기존 토큰은 폐기해요. 예전 토큰이 유출돼도 한 번 재발급이 일어나면 쓸 수 없게 돼요.",[S2(33),S2(34)],"HELPFUL"),
 ("임베딩 모델을 바꾸면 기존 데이터는 어떻게 해야 해?","모델마다 벡터 차원과 값이 달라서 기존 벡터와 비교할 수 없어요. 자료를 다시 적재해야 해요.",[S1(20)],"NOT_HELPFUL"),
 ("Spring Security에서 인증과 인가는 뭐가 달라?","인증은 사용자가 누구인지 확인하는 과정이고, 인가는 확인된 사용자가 그 자원에 접근할 권한이 있는지 확인하는 과정이에요.",[S2(5)],None),
 ("PromptTemplate은 왜 쓰는 거야?","질문과 검색 결과를 정해진 형식에 끼워 넣어 매번 같은 구조의 프롬프트를 만들 수 있어요. 시스템 지시와 사용자 입력을 분리하기도 쉬워요.",[S1(16)],"HELPFUL"),
 ("CORS는 왜 설정해야 해?","브라우저는 다른 출처로 보내는 요청을 기본적으로 막아요. 서버가 허용할 출처를 응답 헤더로 알려 줘야 화면에서 API를 부를 수 있어요.",[S2(42)],None),
 ("Access Token 만료 시간을 짧게 두는 이유는?","Access Token은 매 요청에 쓰여 유출될 기회가 많아요. 수명을 짧게 두면 유출돼도 쓸 수 있는 시간이 줄어들어요.",[S2(30)],"HELPFUL"),
 ("LCEL 체인은 어떻게 연결해?","파이프(|) 연산자로 프롬프트, 모델, 출력 파서를 차례로 이어 하나의 체인으로 만들어요.",[S1(22),S1(23)],None),
 ("BCrypt는 같은 비밀번호도 왜 매번 결과가 달라?","해시할 때마다 무작위 솔트를 섞기 때문이에요. 솔트는 결과 안에 함께 저장돼서 비교할 때 다시 쓰여요.",[S2(12)],"HELPFUL"),
 ("벡터 DB에서 메타데이터 필터는 언제 써?","검색할 때 특정 조건(예: 소유자, 문서 id)에 맞는 청크만 대상으로 삼고 싶을 때 써요.",[S1(27)],None),
 ("Kubernetes 배포 방법도 알려 줘","올린 자료에서 관련 내용을 찾지 못했어요. 해당 내용이 담긴 자료를 올린 뒤 다시 질문해 주세요.",[],None),
]
start=datetime(2026,11,9,14,32)
chats=[]
for i,(q,a,src,fb) in enumerate(qa):
    chats.append({"id":31-i,"memberId":1,"question":q,"answer":a,"sources":src,"feedback":fb,
                  "createdAt":(start-timedelta(hours=2*i+i%3,minutes=7*i)).strftime('%Y-%m-%dT%H:%M:%S')})
chats.append({"id":201,"memberId":5,"question":"다른 회원의 질문","answer":"다른 회원의 답변","sources":[{"documentId":21,"documentName":"다른회원_자료.pdf","page":3}],"feedback":None,"createdAt":"2026-11-08T15:00:00"})
w('data/chats.json',chats)
def pub_chat(c): return {k:c[k] for k in ["id","question","answer","sources","feedback","createdAt"]}

st=[c for c in chats if c["memberId"]==1]
page=lambda items,p,size,total: {"content":items,"page":p,"size":size,"totalElements":total,"totalPages":-(-total//size)}

# requests
w('requests/auth/signup.json',{"email":"newuser@test.com","password":"Test1234!"})
w('requests/auth/login.json',{"email":"student@test.com","password":"Test1234!"})
w('requests/auth/refresh.json',{"refreshToken":"mock-refresh-token-1"})
w('requests/auth/logout.json',{"refreshToken":"mock-refresh-token-1"})
w('requests/chats/stream.json',{"question":"RAG에서 retriever의 similarity와 mmr 검색은 뭐가 달라?"})
w('requests/chats/feedback.json',{"feedback":"HELPFUL"})

mem=lambda m: {"uuid":m["uuid"],"email":m["email"]}
st_m=members[0]
# auth
w('responses/auth/signup.201.json',ok({"uuid":"77777777-7777-4777-8777-777777777777","email":"newuser@test.com"}))
w('responses/auth/signup.400-invalid-input.json',fail("INVALID_INPUT","비밀번호는 8~20자이며 영문, 숫자, 특수문자를 모두 포함해야 합니다"))
w('responses/auth/signup.409-duplicate-email.json',fail("DUPLICATE_EMAIL","이미 가입된 이메일입니다"))
w('responses/auth/login.200.json',ok({"accessToken":"mock-access-token-1","refreshToken":"mock-refresh-token-1","expiresIn":900,"member":mem(st_m)}))
w('responses/auth/login.401-invalid-credentials.json',fail("INVALID_CREDENTIALS","이메일 또는 비밀번호가 올바르지 않습니다"))
w('responses/auth/login.423-account-locked.json',fail("ACCOUNT_LOCKED","로그인에 여러 번 실패해 계정이 잠겼습니다. 잠시 후 다시 시도해 주세요",{"lockedUntil":"2026-11-09T15:30:00"}))
w('responses/auth/refresh.200.json',ok({"accessToken":"mock-access-token-1-r2","refreshToken":"mock-refresh-token-1-r2","expiresIn":900,"member":mem(st_m)}))
w('responses/auth/refresh.401-invalid-refresh-token.json',fail("INVALID_REFRESH_TOKEN","다시 로그인해 주세요"))
# common
w('responses/common/400-invalid-input.json',fail("INVALID_INPUT","입력값을 확인해 주세요"))
w('responses/common/401-unauthorized.json',fail("UNAUTHORIZED","로그인이 필요합니다"))
w('responses/common/403-forbidden.json',fail("FORBIDDEN","접근 권한이 없습니다"))
w('responses/common/500-internal-server-error.json',fail("INTERNAL_SERVER_ERROR","일시적인 오류가 발생했습니다"))
# documents
w('responses/documents/upload.201.json',ok({"id":4,"originalFilename":"Day5_Spring_Security.pdf","fileSize":2483112,"status":"READY","createdAt":"2026-11-09T10:12:00"}))
w('responses/documents/upload.400-invalid-file-type.json',fail("INVALID_FILE_TYPE","PDF 파일만 올릴 수 있습니다"))
w('responses/documents/upload.400-empty-file.json',fail("EMPTY_FILE","빈 파일은 올릴 수 없습니다"))
w('responses/documents/upload.413-file-too-large.json',fail("FILE_TOO_LARGE","파일 크기는 10MB 이하여야 합니다"))
w('responses/documents/upload.422-text-extraction-failed.json',fail("TEXT_EXTRACTION_FAILED","문서에서 글자를 읽지 못했습니다. 스캔한 PDF는 지원하지 않습니다"))
w('responses/documents/upload.503-ai-unavailable.json',fail("AI_UNAVAILABLE","지금은 자료를 처리할 수 없습니다. 잠시 후 다시 시도해 주세요"))
w('responses/documents/list.200.json',ok([pub_doc(d) for d in sorted([d for d in docs if d["memberId"]==1],key=lambda d:d["createdAt"],reverse=True)]))
w('responses/documents/list-indexing-only.200.json',ok([pub_doc(d) for d in docs if d["memberId"]==3]))
w('responses/documents/list-empty.200.json',ok([]))
w('responses/documents/delete.404-document-not-found.json',fail("DOCUMENT_NOT_FOUND","자료를 찾을 수 없습니다"))
# chats
w('responses/chats/list.200-page0.json',ok(page([pub_chat(c) for c in st[:10]],0,10,len(st))))
w('responses/chats/list.200-page1.json',ok(page([pub_chat(c) for c in st[10:]],1,10,len(st))))
w('responses/chats/list-empty.200.json',ok(page([],0,10,0)))
w('responses/chats/feedback.200.json',ok({"id":31,"feedback":"HELPFUL"}))
w('responses/chats/feedback.404-chat-not-found.json',fail("CHAT_NOT_FOUND","질문 기록을 찾을 수 없습니다"))
w('responses/chats/stream.400-no-document.json',fail("NO_DOCUMENT","답변에 쓸 수 있는 자료가 아직 없습니다. 자료를 먼저 올려 주세요"))

# SSE
def sse(events): return ''.join(f"event: {e}\ndata: {json.dumps(d,ensure_ascii=False,separators=(',',':'))}\n\n" for e,d in events)
tok=["similarity는 ","질문과 가장 비슷한 문서를 ","점수 순서대로 k개 가져오는 방식이에요. ","mmr은 비슷한 정도에 더해 ","이미 고른 문서와 겹치지 않는 정도도 ","함께 따져서 다양한 내용을 골고루 가져와요."]
ok_ev=[("sources",[S1(12),S1(14)])]+[("token",{"text":t}) for t in tok]+[("done",{"chatId":32})]
na_ev=[("sources",[S1(27)])]+[("token",{"text":t}) for t in ["올린 자료에서 ","관련 내용을 찾지 못했어요. ","해당 내용이 담긴 자료를 올린 뒤 다시 질문해 주세요."]]+[("done",{"chatId":33})]
er_ev=[("sources",[S2(31)]),("token",{"text":"토큰 원문이 "}),("error",{"message":"지금은 답변할 수 없습니다. 잠시 후 다시 시도해 주세요"})]
for name,ev in [("stream-success",ok_ev),("stream-not-found",na_ev),("stream-error",er_ev)]:
    wt(f'sse/{name}.txt',sse(ev))
    w(f'sse/{name}.events.json',[{"event":e,"data":d} for e,d in ev])

# internal (Backend가 쓰는 가짜 AI 응답)
w('internal/ingest.200.json',{"documentId":4,"chunkCount":57})
w('internal/ingest.422-text-extraction-failed.json',{"error":"TEXT_EXTRACTION_FAILED"})
for status, code in [
    (400, 'INVALID_INPUT'), (400, 'EMPTY_FILE'), (400, 'INVALID_FILE_TYPE'),
    (409, 'DOCUMENT_ALREADY_EXISTS'), (409, 'INGESTION_IN_PROGRESS'),
    (413, 'FILE_TOO_LARGE'), (503, 'EMBEDDING_ERROR'), (503, 'STORAGE_ERROR'),
    (503, 'INGESTION_TIMEOUT'), (500, 'INTERNAL_ERROR'),
]:
    w(f'internal/ingest.{status}-{code.lower().replace("_", "-")}.json', {'error':code})
w('internal/ingest.401-unauthorized.json', {'detail':'Unauthorized'})
wt('internal/query-stream-success.txt',sse([("sources",[S1(12),S1(14)])]+[("token",{"text":t}) for t in tok]+[("done",{})]))
wt('internal/query-stream-error.txt',sse([("sources",[S2(31)]),("token",{"text":"토큰 원문이 "}),("error",{"code":"LLM_ERROR"})]))
print("ok")
