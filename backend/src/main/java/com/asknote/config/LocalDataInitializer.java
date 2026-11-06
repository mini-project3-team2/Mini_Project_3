package com.asknote.config;

import com.asknote.entity.ChatHistory;
import com.asknote.entity.Document;
import com.asknote.entity.Feedback;
import com.asknote.entity.Member;
import com.asknote.repository.ChatHistoryRepository;
import com.asknote.repository.DocumentRepository;
import com.asknote.repository.MemberRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * [local 프로필 전용] 로컬 테스트 데이터 (mock-data 와 같은 계정)
 * - student@test.com: 자료 3개(READY 2 · INDEXING 1), 질문 기록 12개 (페이징 확인용)
 * - other@test.com : 자료 1개, 기록 1개 (남의 자료 · 기록 403 확인용)
 * 이미 student@test.com 이 있으면 넣지 않는다. 비밀번호는 mock-data/README 참고
 */
@Slf4j
@Component
@Profile("local")
@RequiredArgsConstructor
public class LocalDataInitializer implements ApplicationRunner {

    private static final String SOURCES =
            "[{\"documentId\":%d,\"documentName\":\"%s\",\"page\":%d}]";

    private final MemberRepository memberRepository;
    private final DocumentRepository documentRepository;
    private final ChatHistoryRepository chatHistoryRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (memberRepository.existsByEmail("student@test.com")) {
            return;
        }
        String password = passwordEncoder.encode("Test1234!");

        Member student = memberRepository.save(Member.createMember("student@test.com", password));
        Member other = memberRepository.save(Member.createMember("other@test.com", password));

        Document security = ready(student, "Day5_Spring_Security.pdf", 2_457_600L);
        Document jpa = ready(student, "Day3_JPA_기초.pdf", 1_048_576L);
        documentRepository.save(new Document(student, "Day6_Docker.pdf", 3_145_728L)); // INDEXING
        Document otherDoc = ready(other, "다른사람_자료.pdf", 512_000L);

        for (int i = 1; i <= 12; i++) {
            Document source = (i % 2 == 0) ? security : jpa;
            ChatHistory chat = chatHistoryRepository.save(new ChatHistory(
                    student,
                    "테스트 질문 " + i,
                    "테스트 답변 " + i + " — 자료 내용을 근거로 한 답변입니다.",
                    SOURCES.formatted(source.getId(), source.getOriginalFilename(), i)));
            if (i % 3 == 0) {
                chat.updateFeedback(Feedback.HELPFUL);
            }
        }
        chatHistoryRepository.save(new ChatHistory(
                other, "다른 사람 질문", "다른 사람 답변",
                SOURCES.formatted(otherDoc.getId(), otherDoc.getOriginalFilename(), 1)));

        log.info("[local] 테스트 데이터 생성: student@test.com, other@test.com");
    }

    private Document ready(Member member, String filename, long size) {
        Document document = new Document(member, filename, size);
        document.markReady();
        return documentRepository.save(document);
    }
}
