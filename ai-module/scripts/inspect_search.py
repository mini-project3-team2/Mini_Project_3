"""검색 점수 진단(#53 기준값 조정용). 실제 search()와 같은 임베딩·컬렉션·where로 조회.

관련도 필터(MAX_DISTANCE) 적용 전 상위 k개의 거리 값을 보고, 어떤 조각이 필터에
걸리는지/애초에 상위에 못 드는지 확인한다. 서비스 코드(search·filter·라우터)는
수정하지 않고 재사용만 한다.

질문 1건당 OpenAI 임베딩을 1회 호출한다(--run-live 필요). LLM은 호출하지 않는다.
키·예외 원문은 출력하지 않는다.
"""
import argparse
import asyncio
from pathlib import Path
import sys


def _find_src_root() -> Path:
    """이 파일 위치에서 위로 올라가며 src/ 폴더가 있는 디렉터리를 찾아 반환한다.

    로컬(ai-module/scripts/inspect_search.py)에서는 ai-module/을, 컨테이너
    (/app/inspect_search.py)에서는 /app/을 찾는다. 그 디렉터리를 sys.path에 넣으면
    양쪽 모두에서 'from src...' import가 동작한다. (.env 읽기는 load_settings()가
    환경변수를 우선 사용하므로, 컨테이너에 .env가 없어도 Compose 주입 변수로 동작한다.)
    """
    here = Path(__file__).resolve()
    for directory in (here.parent, *here.parents):
        if (directory / "src").is_dir():
            return directory
    raise RuntimeError("src 폴더를 찾지 못했습니다")


sys.path.insert(0, str(_find_src_root()))

from src.core.config import load_settings
from src.core.embeddings import open_embeddings
from src.services.vectorstore import (
    MAX_DISTANCE,
    owner_document_filter,
    open_collection,
)

PREVIEW = 80
K_MAX = 50


async def main(question: str, owner_uuid: str, document_ids: list[int], k: int) -> int:
    settings = load_settings()
    print(f"collection={settings.collection_name} MAX_DISTANCE={MAX_DISTANCE} k={k}")
    print(f"owner_uuid={owner_uuid} document_ids={document_ids}")

    # 실제 search()와 동일: 같은 임베딩 모델로 질문을 aembed_query 1회.
    async with open_embeddings(settings) as embeddings:
        query_vector = await embeddings.aembed_query(question)

    where = owner_document_filter(owner_uuid, document_ids)
    async with open_collection(settings) as collection:
        result = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_vector],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    if not documents:
        print("결과 없음 (where 필터에 맞는 청크가 없음)")
        return 0

    print(f"{'rank':>4}  {'doc_id':>6}  {'page':>4}  {'distance':>9}  {'pass':>4}  preview")
    for rank, (text, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        metadata = metadata or {}
        doc_id = metadata.get("document_id")
        name = str(metadata.get("document_name", ""))
        page = metadata.get("page")
        passed = "PASS" if distance <= MAX_DISTANCE else "DROP"
        preview = " ".join(str(text).split())[:PREVIEW]
        print(f"{rank:>4}  {doc_id:>6}  {page:>4}  {distance:>9.4f}  {passed:>4}  {name} | {preview}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="검색 점수 진단(실제 OpenAI 임베딩 1회 호출, 과금 가능). --run-live 없으면 호출하지 않음."
    )
    parser.add_argument("--run-live", action="store_true", help="실제 임베딩 API를 1회 호출한다.")
    parser.add_argument("--question", required=True, help="질문 문자열")
    parser.add_argument("--owner-uuid", required=True, help="소유자 UUID (members.uuid)")
    parser.add_argument("--document-ids", type=int, nargs="+", required=True,
                        help="READY 문서 id 목록 (documents.id)")
    parser.add_argument("--k", type=int, default=8, help="가져올 상위 개수 (기본 8)")
    args = parser.parse_args()

    if not args.run_live:
        parser.print_help()
        sys.exit(0)
    if not (1 <= args.k <= K_MAX):
        print(f"--k 는 1~{K_MAX} 범위여야 합니다.")
        sys.exit(2)

    try:
        exit_code = asyncio.run(main(args.question, args.owner_uuid, args.document_ids, args.k))
    except Exception as error:
        # 키·예외 원문·트레이스를 출력하지 않는다.
        print(f"실패: {type(error).__name__}")
        exit_code = 1
    sys.exit(exit_code)
