package com.asknote.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

class PdfValidatorTest {

    private final PdfValidator validator = new PdfValidator();

    private static MockMultipartFile file(String name, byte[] content) {
        return new MockMultipartFile("file", name, "application/pdf", content);
    }

    private static byte[] pdf() {
        return "%PDF-1.4\n% test pdf\n".getBytes(StandardCharsets.US_ASCII);
    }

    private static void assertCode(MockMultipartFile f, ErrorCode code) {
        assertThatThrownBy(() -> new PdfValidator().validate(f))
                .isInstanceOf(BusinessException.class)
                .extracting(e -> ((BusinessException) e).getErrorCode())
                .isEqualTo(code);
    }

    @Test
    void 정상_PDF_는_통과() {
        assertThatCode(() -> validator.validate(file("note.pdf", pdf()))).doesNotThrowAnyException();
    }

    @Test
    void 확장자_대문자도_통과() {
        assertThatCode(() -> validator.validate(file("NOTE.PDF", pdf()))).doesNotThrowAnyException();
    }

    @Test
    void 빈_파일은_EMPTY_FILE() {
        assertCode(file("note.pdf", new byte[0]), ErrorCode.EMPTY_FILE);
    }

    @Test
    void null_파일은_EMPTY_FILE() {
        assertThatThrownBy(() -> validator.validate(null))
                .isInstanceOf(BusinessException.class)
                .extracting(e -> ((BusinessException) e).getErrorCode())
                .isEqualTo(ErrorCode.EMPTY_FILE);
    }

    @Test
    void 확장자가_pdf_가_아니면_INVALID_FILE_TYPE() {
        assertCode(file("note.txt", pdf()), ErrorCode.INVALID_FILE_TYPE);
    }

    @Test
    void 파일명이_없으면_INVALID_FILE_TYPE() {
        assertCode(file(null, pdf()), ErrorCode.INVALID_FILE_TYPE);
    }

    @Test
    void 확장자만_pdf_인_텍스트_파일은_INVALID_FILE_TYPE() {
        assertCode(file("fake.pdf", "hello world".getBytes(StandardCharsets.UTF_8)), ErrorCode.INVALID_FILE_TYPE);
    }

    @Test
    void 다섯_바이트보다_짧은_파일은_INVALID_FILE_TYPE() {
        assertCode(file("short.pdf", "%PDF".getBytes(StandardCharsets.US_ASCII)), ErrorCode.INVALID_FILE_TYPE);
    }

    @Test
    void 십MB_초과는_FILE_TOO_LARGE() {
        byte[] big = new byte[(int) PdfValidator.MAX_FILE_SIZE + 1];
        System.arraycopy(pdf(), 0, big, 0, 5);
        assertCode(file("big.pdf", big), ErrorCode.FILE_TOO_LARGE);
    }
}
