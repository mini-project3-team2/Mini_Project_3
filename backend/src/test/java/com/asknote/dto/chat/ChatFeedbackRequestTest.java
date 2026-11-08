package com.asknote.dto.chat;

import static org.assertj.core.api.Assertions.assertThat;

import com.asknote.entity.Feedback;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

/** 피드백 요청 본문 → (JSON 변환 + @Valid) 결과. 변환 실패 · 검증 실패 모두 실제 API 에서는 400 INVALID_INPUT */
class ChatFeedbackRequestTest {

    private final JsonMapper mapper = JsonMapper.builder().build();
    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

    /** 변환에 실패하거나 검증 오류가 있으면 true */
    private boolean rejected(String json) {
        try {
            ChatFeedbackRequest request = mapper.readValue(json, ChatFeedbackRequest.class);
            return !validator.validate(request).isEmpty();
        } catch (JacksonException e) {
            return true;
        }
    }

    @Test
    void HELPFUL_NOT_HELPFUL_만_허용() {
        assertThat(rejected("{\"feedback\":\"HELPFUL\"}")).isFalse();
        assertThat(rejected("{\"feedback\":\"NOT_HELPFUL\"}")).isFalse();
        assertThat(new ChatFeedbackRequest("NOT_HELPFUL").toFeedback()).isEqualTo(Feedback.NOT_HELPFUL);
    }

    @Test
    void 숫자_소문자_다른값_null_은_거부() {
        assertThat(rejected("{\"feedback\":0}")).isTrue();
        assertThat(rejected("{\"feedback\":1}")).isTrue();
        assertThat(rejected("{\"feedback\":true}")).isTrue();
        assertThat(rejected("{\"feedback\":\"helpful\"}")).isTrue();
        assertThat(rejected("{\"feedback\":\"GOOD\"}")).isTrue();
        assertThat(rejected("{\"feedback\":\" HELPFUL\"}")).isTrue();
        assertThat(rejected("{\"feedback\":null}")).isTrue();
        assertThat(rejected("{}")).isTrue();
    }
}
