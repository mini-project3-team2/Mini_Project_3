package com.asknote.common.auth;

import com.asknote.entity.Member;

/**
 * 로그인 회원 조회 — 서비스는 이 인터페이스로만 현재 회원을 얻는다
 * (요청 body · 파라미터로 받은 회원 id · uuid 는 쓰지 않는다: IDOR · RAG 소유자 우회 방지)
 *
 * 구현: JwtCurrentMemberProvider (SecurityContext 의 uuid → 회원 조회)
 *
 * 사용 예: Long memberId = currentMemberProvider.getCurrentMember().getId();
 */
public interface CurrentMemberProvider {

    /** 로그인 회원 — 없으면 BusinessException(UNAUTHORIZED) */
    Member getCurrentMember();
}
