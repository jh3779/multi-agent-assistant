# YouTube 도구 실패 대안 호출 설계

> **상태(2026-11-26 확인): 미구현 설계.** 이 설계가 전제하는 `youtube_search`·`youtube_transcript` 도구와 `TechAgent` 연동은 현재 `main` 코드에 존재하지 않는다(`TechAgent`의 도구는 웹 검색뿐, `app/llms/tech.py`). 설계 기록으로만 보존한다.

## 목적

유튜브 검색 또는 자막 조회가 실패해도 에이전트 실행을 중단하지 않고, AI가 실패 결과를 확인해 다른 입력으로 대안을 시도하게 한다.

## 원인

현재 YouTube 도구의 `ToolException`이 에이전트에 오류 `ToolMessage`로 반환되지 않고 실행 경계 밖으로 전파된다. 따라서 AI가 실패를 인식하거나 다른 도구 호출을 선택할 기회가 없다.

## 변경 범위

- 기존 `create_agent`에 LangChain의 `ToolErrorMiddleware`를 추가한다.
- 미들웨어는 `youtube_search`와 `youtube_transcript`에만 적용한다.
- 예외 세부 내용은 노출하지 않고, 같은 입력을 반복하지 말고 다른 영상 또는 검색어를 사용하라는 오류 메시지를 AI에 반환한다.
- 사용자 요청에 따라 테스트 코드는 추가하지 않는다.

## 동작

1. YouTube 도구가 성공하면 기존 결과를 그대로 사용한다.
2. `youtube_transcript`가 실패하면 AI는 다른 `video_id`를 선택한다.
3. `youtube_search`가 실패하면 AI는 검색어를 바꿔 다시 검색한다.
4. 대안도 실패하면 정보를 가져오지 못했음을 답변한다.

## 제외 범위

- 같은 입력을 자동 반복하는 `ToolRetryMiddleware`
- 별도 LangGraph 재시도 분기
- 재시도 횟수를 강제하는 상태 관리
