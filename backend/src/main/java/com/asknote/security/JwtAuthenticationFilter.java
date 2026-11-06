package com.asknote.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Authorization: Bearer <access token> 검증 → SecurityContext 에 uuid · ROLE 저장
 * 토큰이 없거나 유효하지 않으면 인증 없이 통과 → 인증 필요 경로면 EntryPoint 가 401
 * (빈으로 등록하지 않음: 서블릿 필터로 중복 등록되는 것을 막기 위해 SecurityConfig 에서 생성)
 */
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final String BEARER = "Bearer ";

    private final JwtTokenProvider jwtTokenProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header != null && header.startsWith(BEARER)) {
            jwtTokenProvider.parse(header.substring(BEARER.length())).ifPresent(claims -> {
                var authority = new SimpleGrantedAuthority("ROLE_" + jwtTokenProvider.getRole(claims));
                var authentication = new UsernamePasswordAuthenticationToken(
                        claims.getSubject(), null, List.of(authority));
                SecurityContextHolder.getContext().setAuthentication(authentication);
            });
        }
        chain.doFilter(request, response);
    }
}
