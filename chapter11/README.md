# Chapter 11 설치 안내

## 설치

```bash
pip install -r requirements.txt
```

> **macOS (Apple Silicon · M1 이상) 사용자**는 아래 *pybullet 빌드 오류 해결*을 먼저 진행하세요.
> Windows · Linux · Intel Mac 은 위 명령으로 바로 설치됩니다.

---

## macOS(Apple Silicon)에서 pybullet 빌드 오류

`pip install pybullet` 실행 시 휠(wheel) 빌드가 다음처럼 실패합니다.

```
error: command '/usr/bin/clang' failed with exit code 1
ERROR: Failed building wheel for pybullet
```

### 원인 (장비 문제가 아니라 pybullet 패키징 문제)

pybullet 은 Apple Silicon 용으로 **미리 빌드된 휠을 제공하지 않아** 소스에서 직접 컴파일됩니다.
그런데 함께 들어있는 **오래된 zlib**(`examples/ThirdPartyLibs/zlib/zutil.h`)가
`TARGET_OS_MAC`(요즘 맥에선 항상 `1`)을 **클래식 맥OS(System 7~9)** 신호로 오인해
`#define fdopen NULL` 을 적용하고, 이 매크로가 시스템 헤더 `<stdio.h>` 의 `fdopen` 선언을
깨뜨립니다. Apple clang 16+ 의 엄격해진 헤더 처리 때문에 표면화된 문제입니다.

### 해결 1 — 소스 패치 후 설치 (현재 Python 그대로 사용)

Xcode 커맨드라인 도구가 필요합니다.

```bash
xcode-select --install      # 이미 설치돼 있으면 건너뜀

mkdir tmp
cd /tmp
pip download --no-binary :all: --no-deps pybullet -d pb
cd pb && tar xzf pybullet-*.tar.gz && cd pybullet-*/

# 번들 zlib 의 '클래식 맥OS' 분기를 꺼서 fdopen 매크로 충돌 제거
old='#if defined(MACOS) || defined(TARGET_OS_MAC)'
new='#if defined(MACOS_CLASSIC_DISABLED)'
sed -i '' "s/$old/$new/" examples/ThirdPartyLibs/zlib/zutil.h

pip install .               # 컴파일에 수 분 소요
```

zlib 한 줄 패치만으로 끝까지 컴파일되며, 만들어지는 휠은 `universal2`(Intel·Apple Silicon 공용)입니다.
이후 chapter11 디렉터리로 돌아와 나머지 패키지를 설치합니다(이미 깔린 pybullet 은 건너뜀).

```bash
pip install -r requirements.txt
```

### 해결 2 — conda 사용 (컴파일 없음)

conda 환경을 쓴다면 미리 빌드된 바이너리를 바로 받을 수 있습니다.

```bash
conda install -c conda-forge pybullet
```

단, 이후 챕터 코드도 **같은 conda 환경의 Python** 으로 실행해야 합니다.

---

## 설치 확인

```bash
python3 smoke_test.py
```

다음이 출력되면 정상입니다.

```
카메라 OK: 320 x 240 픽셀
```
