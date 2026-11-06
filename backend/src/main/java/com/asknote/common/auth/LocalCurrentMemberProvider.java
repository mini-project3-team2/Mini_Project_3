package com.asknote.common.auth;

import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.entity.Member;
import com.asknote.repository.MemberRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/**
 * [임시 · local 프로필 전용] JWT 인증이 붙기 전까지 고정 테스트 회원을 로그인 회원으로 돌려준다
 * - 기본: student@test.com (LocalDataInitializer 가 생성)
 * - 남의 자료 접근(403) 확인: 실행 옵션 --asknote.local.member-email=other@test.com
 * JWT 인증 구현이 병합되면 이 클래스는 삭제한다
 */
@Component
@Profile("local")
@RequiredArgsConstructor
public class LocalCurrentMemberProvider implements CurrentMemberProvider {

    private final MemberRepository memberRepository;

    @Value("${asknote.local.member-email:student@test.com}")
    private String memberEmail;

    @Override
    public Member getCurrentMember() {
        return memberRepository.findByEmail(memberEmail)
                .orElseThrow(() -> new BusinessException(ErrorCode.UNAUTHORIZED));
    }
}
