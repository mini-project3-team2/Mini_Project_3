package com.asknote.security;

import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.entity.Member;
import com.asknote.repository.MemberRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

/** JWT 인증 회원 — SecurityContext 의 uuid(JWT subject) 로 회원 조회 */
@Component
@RequiredArgsConstructor
public class JwtCurrentMemberProvider implements CurrentMemberProvider {

    private final MemberRepository memberRepository;

    @Override
    public Member getCurrentMember() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof String uuid)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED);
        }
        return memberRepository.findByUuid(uuid)
                .orElseThrow(() -> new BusinessException(ErrorCode.UNAUTHORIZED));
    }
}
