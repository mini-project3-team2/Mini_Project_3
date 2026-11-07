package com.asknote.service;

import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Locale;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

/**
 * 업로드 파일 검증 (API 설계서 4.1) — 구현 담당: Backend 2
 * - 빈 파일 → BusinessException(ErrorCode.EMPTY_FILE)
 * - 확장자 .pdf 가 아니거나, 파일 앞 5바이트가 "%PDF-" 가 아니면 → BusinessException(ErrorCode.INVALID_FILE_TYPE)
 * (10MB 초과는 spring.servlet.multipart 설정이 먼저 막고 전역 예외 처리가 413 으로 응답)
 */
@Component
public class PdfValidator {

    /** application.yaml 의 spring.servlet.multipart.max-file-size 와 같은 값 */
    static final long MAX_FILE_SIZE = 10L * 1024 * 1024;

    private static final String PDF_EXTENSION = ".pdf";
    private static final byte[] PDF_MAGIC = "%PDF-".getBytes(StandardCharsets.US_ASCII);

    public void validate(MultipartFile file) {
        // 1. 빈 파일 (파일 자체가 없거나 0바이트)
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ErrorCode.EMPTY_FILE);
        }

        // 2. 크기 — multipart 설정이 먼저 막지만, 설정이 바뀌어도 10MB 를 넘지 않도록 한 번 더 확인
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BusinessException(ErrorCode.FILE_TOO_LARGE);
        }

        // 3. 확장자 — 대소문자 구분 없이 .pdf 로 끝나야 함
        if (!hasPdfExtension(file.getOriginalFilename())) {
            throw new BusinessException(ErrorCode.INVALID_FILE_TYPE);
        }

        // 4. 내용 — 확장자만 바꾼 파일을 막기 위해 앞 5바이트가 "%PDF-" 인지 확인
        if (!hasPdfMagic(file)) {
            throw new BusinessException(ErrorCode.INVALID_FILE_TYPE);
        }
    }

    private static boolean hasPdfExtension(String filename) {
        if (filename == null) {
            return false;
        }
        return filename.trim().toLowerCase(Locale.ROOT).endsWith(PDF_EXTENSION);
    }

    private static boolean hasPdfMagic(MultipartFile file) {
        try (InputStream in = file.getInputStream()) {
            byte[] head = in.readNBytes(PDF_MAGIC.length);
            return Arrays.equals(head, PDF_MAGIC);
        } catch (IOException e) {
            throw new BusinessException(ErrorCode.INVALID_INPUT);
        }
    }
}
