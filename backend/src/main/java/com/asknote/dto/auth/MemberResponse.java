package com.asknote.dto.auth;

import com.asknote.entity.Member;

/** 회원 정보 응답 (내부 id · 비밀번호는 넣지 않음) — 회원가입 201 의 data, 로그인의 member */
public record MemberResponse(String uuid, String email) {

    public static MemberResponse from(Member member) {
        return new MemberResponse(member.getUuid(), member.getEmail());
    }
}
