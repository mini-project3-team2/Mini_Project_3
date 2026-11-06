package com.asknote.controller;

import com.asknote.common.ApiResponse;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.dto.auth.LoginRequest;
import com.asknote.dto.auth.MemberResponse;
import com.asknote.dto.auth.RefreshRequest;
import com.asknote.dto.auth.SignupRequest;
import com.asknote.dto.auth.TokenResponse;
import com.asknote.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final CurrentMemberProvider currentMemberProvider;

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<MemberResponse> signup(@Valid @RequestBody SignupRequest request,
                                              HttpServletRequest http) {
        return ApiResponse.ok(authService.signup(request, http.getRemoteAddr()));
    }

    @PostMapping("/login")
    public ApiResponse<TokenResponse> login(@Valid @RequestBody LoginRequest request,
                                            HttpServletRequest http) {
        return ApiResponse.ok(authService.login(request, http.getRemoteAddr()));
    }

    @PostMapping("/refresh")
    public ApiResponse<TokenResponse> refresh(@Valid @RequestBody RefreshRequest request,
                                              HttpServletRequest http) {
        return ApiResponse.ok(authService.refresh(request.refreshToken(), http.getRemoteAddr()));
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(@Valid @RequestBody RefreshRequest request, HttpServletRequest http) {
        authService.logout(currentMemberProvider.getCurrentMember(), request.refreshToken(), http.getRemoteAddr());
    }
}
