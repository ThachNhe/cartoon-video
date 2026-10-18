# BitByBit: video hoạt hình dạy lập trình

Kênh **BitByBit** làm video hoạt hình ngắn giải thích khái niệm lập trình, dựng bằng Manim. Nhân vật chính là **Bit**, một robot màu xanh. Mỗi video được đăng ở hai dạng:

| Dạng | Tỉ lệ | Nền tảng |
|---|---|---|
| Bản đầy đủ | 16:9, 2560×1440 | YouTube (video thường). YouTube nén video từ 1440p trở lên bằng chuẩn tốt hơn, chữ trong code nét hơn |
| Bản ngắn | 9:16, 1440×2560 | YouTube Shorts + Facebook Reels: một file dùng cho cả hai (YouTube nén Shorts 1440p tốt hơn; Facebook tự thu về 1080×1920) |

Fanpage Facebook chỉ đăng Reels (bản 9:16). Không làm bản 16:9 1080p cho Facebook nữa (bỏ từ 2026-10-18).

Trả lời người dùng bằng **tiếng Việt**. Code, comment và chữ trong video viết bằng **tiếng Anh**.

## Môi trường

- WSL2 (Ubuntu), Python trong `.venv/`: manim 0.22, ManimPango, neutts 1.4 (TTS, chạy trên GPU CUDA), torch, soundfile. Máy cần có ffmpeg.
- `.env` chứa `HF_TOKEN` để tải model TTS. Không in nội dung file này ra và không commit nó.
- `media/` nằm trong `.gitignore` và chứa toàn bộ kết quả render.

## Cấu trúc

```
bitbybit.py          Thư viện dùng chung: Bit, thương hiệu, narrator, SFX, mastering âm thanh, pick()/SHORT,
                     BitScene (lớp cơ sở của mọi video) và ThumbnailMixin
<video>.py           Mỗi video: `from bitbybit import *` + các cảnh riêng của nó (+ class Thumbnail)
qc.py                Kiểm tra chất lượng video đã render, tự render lại khi cần (xem mục Kiểm tra chất lượng)
channel_art.py       Ảnh bìa fanpage Facebook (1640×856, 3 phương án); bản đã xuất ở media/channel_art/
assets/fonts/        Poppins (chữ thường), JetBrains Mono NL (code; bản NL không có ligature, manim cần vậy)
assets/sfx/          Hiệu ứng âm thanh, tự sinh bằng make_sfx() nếu thiếu file
assets/voice/        Cache giọng đọc đã tạo (được commit, nên render lại không cần chạy TTS)
assets/voice_ref/    Giọng mẫu: dave.pt (codes đã encode), dave.txt (transcript)
media/videos/<video>/1440p30/   Bản 16:9 cho YouTube (2560×1440)
media/videos/<video>/2560p30/   Bản 9:16 cho Shorts + Reels (1440×2560)
```

## Render

```bash
.venv/bin/manim -qh -r 2560,1440 --fps 30 <video>.py <Scene>          # 16:9 cho YouTube (1440p)
BIT_FORMAT=vertical .venv/bin/manim -qh -r 1440,2560 --fps 30 <video>.py <Scene>   # 9:16 cho Shorts + Reels (1440p)
.venv/bin/manim -ql <video>.py <Scene>                                # xem nhanh, chất lượng thấp
BIT_VOICE=0 ...                                                       # render không có lồng tiếng
.venv/bin/manim -s -r 2048,2048 recursion.py ChannelAvatar            # avatar kênh (vuông)
.venv/bin/manim -s -t -r 2048,2048 recursion.py ChannelAvatarRound    # avatar tròn, nền trong suốt
.venv/bin/manim -s -r 1280,720 recursion.py Thumbnail                 # thumbnail YouTube (1280×720)
```

Ảnh tĩnh nằm ở `media/images/<video>/`. Thumbnail đã chọn được chép sang `media/thumbnails/`.

Render chất lượng cao mất vài phút, nên chạy ở chế độ nền.

## Quy ước chung (áp dụng cho mọi video)

### Hai tỉ lệ trong cùng một file
- `VERTICAL = BIT_FORMAT == "vertical"`. Khung dọc rộng 8 × cao 14.22 đơn vị, cùng mật độ điểm ảnh như khung 16:9 (14.22 × 8; 180 px/đơn vị ở 1440p), nên mọi thứ giữ nguyên kích thước. Không có `-r` thì `BIT_FORMAT=vertical` tự đảo khung -qh 1920×1080 thành 1080×1920.
- `pick(wide, tall)` trả về giá trị theo tỉ lệ đang render. Mọi tọa độ hoặc kích thước khác nhau giữa hai bản đều đi qua `pick()`. Đặt vị trí theo `config.frame_width` / `frame_height` thay cho số cố định.
- `SHORT = VERTICAL`: bản ngắn mở đầu bằng hook và cắt bớt nhịp chậm. Bọc phần chỉ có ở bản dài bằng `if not SHORT:`. **Bản 16:9 phải giữ nguyên** khi sửa cho bản dọc.

### Bản dọc (Shorts/Reels)
- **Vùng an toàn:** Shorts và Reels đè nút bấm lên các góc, mép phải và khoảng 25% phía dưới màn hình. Đặt nội dung chính ở giữa. Watermark nằm giữa phía trên (`to_edge(UP, buff=1.0)`).
- **Mở đầu (cold open):** khung hình đầu tiên phải là cảnh hấp dẫn nhất của video, kèm một câu hỏi. Khung này thường được dùng làm ảnh xem trước. Không bắt đầu bằng màn hình trống hay fade-in.
- **Độ dài:** nhắm khoảng 60–70 giây.
- **Chữ dài:** ngắt thành nhiều dòng (dùng `VGroup` gồm nhiều `Text` rồi `arrange(DOWN)`) để vừa chiều ngang 8 đơn vị.

### Thương hiệu
- **Watermark** (`watermark()`): icon cao 0.42, đầu bot cao 6.8 (viền cam mỏng), chữ trắng cỡ 19, độ đậm 42%. Toàn bộ được vẽ thành ảnh trước bằng `flatten()` rồi mới làm mờ. Không dùng `fade()` cho watermark, vì nó làm mờ từng lớp riêng và các lớp sẽ lộ ra nhau. Ở bản 16:9 watermark nằm góc trên phải.
- **Bộ thương hiệu:** `channel_icon()` (đầu Bit trên đĩa cam; `head_height` mặc định 5.4 dùng cho avatar kênh), `wordmark()` (chữ BitByBit, dấu chấm chữ "i" là bóng đèn ăng-ten).
- **Bảng màu:** `BG #1B1E3C`, `ACCENT #FFD54F`, `HEADLINE #FF6B35`, `TEXT_LIGHT`, `TEXT_MUTED`, `FRAME_COLORS`.
- **Cảnh kết:** thẻ kênh (avatar, tên, tagline) và nút SUBSCRIBE. Nút "nhịp thở" kèm vòng sóng trong lúc Bit nói. Khi bấm: tiếng click, gợn sóng, nút đổi sang "✓ SUBSCRIBED", pháo giấy, Bit ăn mừng. Xem `subscribe_card()`, `pulse()`, `confetti()`.

### Lồng tiếng và âm thanh
- `Narrator` (giọng "dave", pitch 1.25) lưu cache theo hash của nội dung câu. Sửa bất kỳ chữ nào trong câu thoại sẽ tạo clip mới (cần GPU và model). Nếu tốc độ đọc bất thường, chương trình tự thử seed khác.
- `say()`: chữ trong bong bóng chính là câu Bit đọc, nên người xem tắt tiếng vẫn hiểu. Chữ IN HOA được đọc như chữ thường. Dùng `speech=` khi cần đọc khác chữ hiển thị (ví dụ "n == 0" đọc là "n equals zero").
- **Không bật lại cache của manim** (`config.disable_caching = True` ở đầu file). Cache của manim 0.22 làm mất các tiếng động xếp ngay sau một đoạn lấy từ cache, và làm âm thanh trôi lệch so với hình.

### Âm thanh chuẩn
`Recursion.render()` gọi `master_audio()` sau mỗi lần render. Hàm này chuẩn hoá loudnorm hai lượt về **-14 LUFS**, đỉnh **-1.5 dBTP**, và giữ nguyên hình. YouTube và Facebook chuẩn hoá về khoảng -14 LUFS và không tăng âm lượng cho video nhỏ tiếng.

## Kiểm tra chất lượng (bắt buộc trước khi giao video)

```bash
.venv/bin/python qc.py                 # kiểm tra mọi video, cả hai tỉ lệ (exit 1 nếu còn lỗi)
.venv/bin/python qc.py recursion --format vertical
.venv/bin/python qc.py --fix           # tự render lại khi lỗi sửa được bằng render, rồi kiểm tra lại
```

Kết quả nằm trong `media/qc/<video>/`: báo cáo `<format>_report.json`, ảnh lưới khung hình `<format>_sheet.png` và log render.

**Quy trình:** render → `qc.py` → nếu FAIL:
- Lỗi đánh dấu "render lại sẽ sửa được": chạy `qc.py --fix`.
- Lỗi "cần sửa code": sửa code, render lại, chạy `qc.py` lại.

Lặp cho tới khi **ĐẠT**, rồi duyệt ảnh lưới theo checklist bằng mắt bên dưới. WARN không chặn giao video, nhưng phải báo cho người dùng.

### Checklist tự động (`qc.py`)

| Tiêu chí | Ngưỡng | Lỗi thì |
|---|---|---|
| Cache manim đã tắt | có `config.disable_caching = True` | sửa code |
| Có file video, mới hơn code | mtime của mp4 ≥ mtime của file `.py` | render lại |
| Độ phân giải / fps | `wide` 2560×1440, `vertical` 1440×2560; 30fps | render lại |
| Độ dài | 16:9 ≤ 600s; 9:16 cảnh báo > 75s, lỗi > 90s | sửa code |
| Âm thanh đủ tới cuối | dừng trước hình ≤ 5s (bắt lỗi mất tiếng) | render lại |
| Độ to | -14 ± 1.5 LUFS | render lại |
| Đỉnh âm | ≤ -1 dBTP | render lại |
| Khoảng lặng dài nhất | 16:9 cảnh báo > 3.5s, lỗi > 6s; 9:16 cảnh báo > 2.5s, lỗi > 4s | sửa code |
| Hình đứng yên | cảnh báo > 6s | sửa code |
| Khung đầu có nội dung (hook) | ≥ 8% khung hình khác màu nền; bắt buộc ở 9:16, chỉ cảnh báo ở 16:9 | sửa code |
| Watermark luôn hiện | có trong ≥ 95% khung hình mẫu (trừ 1.5s cuối) | sửa code |

Ngưỡng nằm ở đầu `qc.py` (`FORMATS` và các hằng số). Khi thêm video mới, đăng ký nó trong `VIDEOS`.

### Checklist độ thu hút, phần tự động (`[Thu hút]` trong `qc.py`)

Khi render, scene ghi dòng thời gian vào `<Scene>.timeline.json` (cạnh file mp4). Các loại sự kiện:
- `speech`: câu đọc
- `text`: chữ trên màn hình
- `sfx`: tiếng động
- `chapter`: chương
- `moment`: khoảnh khắc chính, gồm `hook`, `topic`, `promise`, `gag`, `reveal`, `twist`, `surprise`, `payoff`, `joke`, `cta`, `loop`

Video mới phải:
- gọi `self.moment(...)` ở đúng các khoảnh khắc đó
- mở mỗi phần bằng `self.chapter(name, title)`; `title` là tên chương trên YouTube
- truyền `captioned=True` cho `voice()` khi chữ đang hiện trên màn hình

| Tiêu chí | Shorts/Reels (9:16) | YouTube (16:9) |
|---|---|---|
| Hook ngay đầu | moment `hook` ở 0s, chữ đầu tiên trước 2s: **bắt buộc** | không áp dụng |
| Nêu chủ đề sớm | cảnh báo > 8s, lỗi > 12s | cảnh báo > 10s, lỗi > 15s |
| Hứa hẹn lý do xem tiếp (`promise`) | không áp dụng (hook đã làm việc này) | trước 15s: **bắt buộc** |
| Kết thúc nối vòng (`loop`) | `loop` trong 6s cuối (cảnh báo) | không áp dụng |
| Mốc chương | không áp dụng | ≥ 3 chương, mỗi chương ≥ 10s (cảnh báo); xuất ra `media/qc/<video>/wide_chapters.txt` |
| Có cao trào (`payoff`) | bắt buộc | bắt buộc |
| Có bất ngờ / hài hước (`gag`/`surprise`/`joke`) | bắt buộc | bắt buộc |
| Khoảng không có gì mới | cảnh báo > 2.5s, lỗi > 4s | cảnh báo > 4s, lỗi > 7s |
| Đổi cảnh / điểm nhấn (chapter, moment) | cảnh báo > 20s, lỗi > 30s | cảnh báo > 30s, lỗi > 45s |
| Kêu gọi đăng ký ở cuối (`cta` tới hết video, hoặc tới `loop` nếu có) | cảnh báo > 10s, lỗi > 15s | cảnh báo > 12s, lỗi > 20s |
| Xem không tiếng vẫn hiểu | mọi câu đọc có chữ: bắt buộc | như bên trái |
| Tốc độ đọc / tỉ lệ có lời dẫn | 120–200 từ/phút, 30–85% thời lượng (cảnh báo) | như bên trái |
| Đủ thời gian đọc chữ | ≥ số từ / 3 giây (cảnh báo) | như bên trái |

### Checklist độ thu hút, phần duyệt nội dung (Claude duyệt kịch bản, người dùng chốt)

Duyệt **trước khi render bản chính**, ghi kết quả vào mục của video trong "Cấu hình từng video". Mọi mục **bắt buộc** phải đạt. Mục **nên có** chưa đạt thì ghi rõ lý do.

**Shorts/Reels (9:16)**

| # | Tiêu chí | Mức |
|---|---|---|
| S1 | 0–2s: hình ảnh cao trào và một câu hỏi gây tò mò, nói thẳng với người xem ("you") | bắt buộc |
| S2 | Câu hỏi ở hook được trả lời rõ trong video | bắt buộc |
| S3 | Chỉ một ý chính, giải thích trong ≤ 3 bước | bắt buộc |
| S4 | Mỗi khái niệm có hình minh hoạ ngay lúc được nói | bắt buộc |
| S5 | Có ít nhất một khoảnh khắc bất ngờ hoặc hài hước ở nửa sau | bắt buộc |
| S6 | Có câu chốt dễ nhớ (takeaway) | bắt buộc |
| S7 | Kết thúc nối vòng về đầu video để người xem xem lại | nên có |
| S8 | Mỗi bong bóng ≤ 2 dòng, khoảng ≤ 12 từ | nên có |

**YouTube (16:9)**

| # | Tiêu chí | Mức |
|---|---|---|
| Y1 | 15 giây đầu: nêu chủ đề và lý do nên xem tiếp (người xem sẽ thấy hoặc học được gì) | bắt buộc |
| Y2 | Mạch truyện rõ: mở vấn đề → minh hoạ → bước ngoặt → câu chốt | bắt buộc |
| Y3 | Mỗi khái niệm có hình minh hoạ ngay lúc được nói | bắt buộc |
| Y4 | Câu chốt được nói rõ ở cuối | bắt buộc |
| Y5 | Tiêu đề và ảnh thumbnail đã lên ý tưởng (ảnh lấy từ khung nào) | nên có |
| Y6 | Có mốc chương (chapter) cho phần mô tả YouTube | nên có |

### Checklist bằng mắt (duyệt `<format>_sheet.png`)
- Không có chữ bị cắt ở mép khung, không có hai thành phần đè lên nhau ngoài ý muốn (bong bóng thoại che code đang giải thích, tiêu đề đè thẻ kênh…).
- 9:16: nội dung chính nằm ngoài vùng bị nút của Shorts/Reels che (25% dưới, mép phải).
- 9:16: khung đầu là cảnh hook kèm câu hỏi.
- Watermark không bị nội dung đè lên.
- Ở các điểm quan trọng (crash, bấm Subscribe), trích khung hình đúng thời điểm có tiếng để xác nhận âm thanh khớp hình.

## Cấu hình từng video

### `recursion.py`: Recursion (đệ quy và base case)

| Mục | Giá trị |
|---|---|
| Scene | `Recursion` (cùng file có `ChannelAvatar`, `ChannelAvatarRound`, `Thumbnail`, `ThumbnailCode`, `ThumbnailStack`) |
| Thumbnail | 3 phương án trong `media/thumbnails/recursion_{A,B,C}.png`: A "1 LINE = CRASH" (`Thumbnail`, đề xuất), B "DON'T DELETE THIS!" (`ThumbnailCode`), C "STACK OVERFLOW!" (`ThumbnailStack`). Chờ người dùng chọn |
| Gợi ý tiêu đề YouTube | "Recursion Explained: The ONE Line That Stops the Crash" / "What Happens If You Delete ONE Line? (Recursion Explained)" / "Recursion in 100 Seconds, and Why Your Code Crashes" |
| Chủ đề | Đệ quy, call stack, base case, `RecursionError` |
| Độ dài | 16:9 khoảng 1:42; 9:16 khoảng 1:10 |
| Giọng đọc | `Narrator(ref="dave", pitch=1.25)` |
| Code minh hoạ | `COUNTDOWN` (có base case), `NO_BASE_CASE` |
| Bố cục 16:9 | Code góc trên trái (`CODE_WIDTH` 6.2), output bên dưới, call stack bên phải (`STACK_X` 4.6) |
| Bố cục 9:16 | Code trên cùng (`CODE_WIDTH` 7.2), output bên trái, call stack bên phải (`STACK_X` 1.85, `STACK_BASE_Y` -4.6, `STACK_TOP_Y` 0.8), Bit góc dưới trái |
| Trạng thái | Đã render cả hai bản (2026-10-17) |

**Mạch truyện** (theo thứ tự các hàm trong `construct()`):
1. `cold_open()`, chỉ bản ngắn: flash cảnh `RecursionError` và câu hỏi "What happens if you delete ONE line?".
2. `intro()`: Bit gõ chữ "RECURSION" trên laptop. Bản dài có màn gõ sai "RECURSOIN" rồi sửa.
3. `meet_bit()`: định nghĩa đệ quy. Bản dài có thêm phần chào hỏi và câu hứa hẹn "Today: RECURSION, and the ONE line that stops it from CRASHING."
4. `happy_path()`: chạy `countdown(3)` với call stack, giải thích base case, rồi xoá base case.
5. `stack_overflow()`: n chạy xuống số âm, "NEGATIVE TWO?!", stack tràn, crash, Bit ngã.
6. `punchline()`: câu đùa "To understand recursion, you must first understand recursion." và đường hầm zoom lồng nhau.
7. `outro()`: tiêu đề "Always write your base case.", thẻ kênh và nút Subscribe. Bản ngắn kết bằng `loop_back()`: Bit nói "...unless someone deletes the base case.", màn hình loé đỏ và Bit mắt chữ X, khớp với khung đầu nên khi video tự phát lại sẽ nối thẳng vào cảnh crash.

**Duyệt nội dung (2026-10-17):**

| Tiêu chí | Kết quả |
|---|---|
| S1 hook | ✅ cảnh `RecursionError` và câu hỏi "What happens if you delete ONE line?" ngay giây đầu |
| S2 trả lời câu hỏi | ✅ xoá base case → stack tràn → crash |
| S3 một ý chính | ✅ base case |
| S4 minh hoạ | ✅ code, output và call stack chạy theo lời giải thích |
| S5 bất ngờ / hài hước | ✅ "NEGATIVE TWO?!", Bit ngã, câu đùa đệ quy và đường hầm |
| S6 câu chốt | ✅ "Always write your base case." |
| S7 kết thúc nối vòng | ✅ `loop_back()`: "...unless someone deletes the base case." rồi nối vào cảnh crash ở đầu |
| S8 bong bóng ngắn | ✅ bản ngắn dùng "That line is the BASE CASE: the exit door." (8 từ); bản dài giữ câu đầy đủ |
| Y1 15 giây đầu | ✅ chủ đề lúc khoảng 6s, câu hứa hẹn "...the ONE line that stops it from CRASHING." trước 15s |
| Y2 mạch truyện | ✅ countdown chạy đúng → xoá base case → crash → câu chốt |
| Y3 minh hoạ | ✅ |
| Y4 câu chốt | ✅ "Lesson learned: ALWAYS write a base case." và tiêu đề ở cảnh kết |
| Y5 tiêu đề / thumbnail | ✅ 3 phương án thumbnail và 3 gợi ý tiêu đề (xem bảng trên), chờ người dùng chọn |
| Y6 mốc chương | ✅ `qc.py` xuất `media/qc/recursion/wide_chapters.txt` để dán vào mô tả YouTube |

**Số liệu sau khi đăng** (điền sau 48 giờ và sau 7 ngày):

| Nền tảng | Ngày đăng | Link | Lượt xem | Viewed vs swiped away / lượt xem 3s | % thời lượng xem TB | Điểm người xem rời đi nhiều nhất |
|---|---|---|---|---|---|---|
| YouTube | | | | — | | |
| YouTube Shorts | | | | | | |
| Facebook Reels | | | | | | |

**Phần chỉ có ở bản dài:** gõ sai tiêu đề; "Hi! I'm Bit" / câu hứa hẹn "Today: RECURSION…" / "Sounds scary?…"; "Is n == 0? Nope…"; "…calls ITSELF with n - 1"; câu base case đầy đủ "That if n == 0 line is…"; "Okay, n is 0, so we… wait."; "Lesson learned…"; "Here's a little joke…"; zoom đường hầm 3 lần (bản ngắn 2 lần); vẫy tay chào rồi mờ dần ở cuối.

**Phần chỉ có ở bản ngắn:** `cold_open()`; câu base case rút gọn; kết thúc nối vòng `loop_back()`.

### Các video tiếp theo (cùng khuôn: `BitScene`, hook + loop ở bản ngắn, thumbnail trong `media/thumbnails/<video>.png`)

Mọi video dưới đây đã qua đủ checklist tự động. Kết quả duyệt nội dung (S1–S8, Y1–Y6) giống nhau ở các điểm chung, nên chỉ ghi phần riêng:
- **Đạt ở mọi video:** hook có câu hỏi; một ý chính; minh hoạ bằng hình; ít nhất một câu đùa; câu chốt ở cảnh kết; kết thúc nối vòng; câu hứa hẹn trước 15s ở bản dài; thumbnail; mốc chương tự sinh.
- **Mở đầu khác nhau giữa các video:** gõ laptop (5 video đầu), ô chữ tự sắp xếp (selection sort), đồ thị commit (git), container mở cửa (Docker).

| Video (file → Scene) | Ý chính & hook (Shorts) | Bố cục / điểm riêng | Câu chốt | Câu đùa | Thumbnail | Gợi ý tiêu đề YouTube |
|---|---|---|---|---|---|---|
| `off_by_one.py` → `OffByOne` | `while i <= len` đi quá 1 bước → `IndexError`. Hook: "Why does this loop crash on the LAST item?" | Ba hộp trái cây là bậc đá; Bit nhảy theo `i`, ngã vào ô 3 không tồn tại. Sửa: `<=` → `<` | "Count from 0, stop at len - 1." | 2 hard things: cache invalidation, naming, off-by-one | "ONE STEP TOO FAR!" | "Why Your Loop Crashes on the LAST Item (Off-by-One Error)" |
| `binary_search.py` → `BinarySearch` | Kiểm tra phần giữa, bỏ một nửa. Hook: "Find 1 number in a MILLION in just 20 guesses?" | Hàng ô ngang (16:9) / cột dọc (9:16). Tuyến tính 11 lần vs nhị phân 4 lần; bộ đếm 1,000,000 → 1 sau 20 bước. Bản dài: phần "list chưa sắp xếp" | "Sorted list? Search in halves." | Binary search tìm chìa khoá: "Step one: sort the whole house." | "1,000,000 in 20 GUESSES" | "Find 1 Number in a MILLION in 20 Guesses (Binary Search)" |
| `aliasing.py` → `Aliasing` | `b = a` không copy. Hook: "Why did my list change BY ITSELF?!" | Nhãn tên `a`/`b` trỏ vào cùng một hộp list; sửa bằng `a.copy()` | "= shares, .copy() copies." | a và b chia tay: "They shared EVERYTHING." | "WHO ADDED 4?!" | "Why Did My Python List Change By Itself? (b = a)" |
| `floating_point.py` → `FloatingPoint` | 0.1 không kết thúc trong hệ nhị phân. Hook: "Why can't Python add 0.1 + 0.2?!" | REPL Python; 1/3 trong thập phân ↔ 0.1 trong nhị phân; `==` → False; sửa bằng `math.isclose` | "Never compare floats with ==." | Ngân hàng dùng float: "$0.30000000000000004" | "0.1 + 0.2 = 0.30000000000000004 WHY?!" | "Why 0.1 + 0.2 Is NOT 0.3 in Python" |
| `hash_map.py` → `HashMap` | `hash()` % số bucket → tra 1 bước. Hook: "How does Python find a key INSTANTLY?" | Máy `hash()`; 8 bucket; giá trị hash là minh hoạ (`HASHES`); va chạm Bit/Ada cùng bucket 4 | "Fast lookups? Use a dict." | Phòng không phải hash map: "Finding my socks takes O(n)." | "1 STEP. Not a million." | "How Python Dicts Find Any Key in ONE Step (Hash Maps)" |
| `selection_sort.py` → `SelectionSort` | Tìm nhỏ nhất, đổi lên đầu, lặp lại. Hook: "Find the smallest. Swap. Repeat. That's it?!" | 6 cột [29,10,14,37,13,5] chạy **cùng khung code**: thanh highlight theo đúng dòng đang chạy (`goto()`: `for i` → `low = i` → `if a[j] < a[low]` → `low = j` → dòng hoán đổi); đếm so sánh (15; 9:16 đặt ở thanh tiêu đề khung code). Bản dài giải thích code trước khi chạy + O(n²); 1 triệu phần tử = 499,999,500,000 so sánh | "Find the smallest. Swap. Repeat." | Số nhỏ nhất tự tin: "It knows it'll be SELECTED first." | "PICK. SWAP. REPEAT." | "Selection Sort Explained Step by Step (with Code)" |
| `git_commands.py` → `GitCommands` | 10 lệnh: init, clone, status, add, commit, log, branch, switch, merge, push (+pull ở bản dài). Hook: "Know these 10 git commands? You'll use them DAILY." | Terminal + sơ đồ Working dir → Staging → Repository → GitHub; vòng vàng là HEAD. Bản dài: mẹo mỗi lệnh + cheat sheet; bản ngắn: một câu ngắn mỗi lệnh | "status, add, commit, push. Repeat!" | "Too many COMMITMENT issues." | "10 GIT COMMANDS you'll use EVERY day" | "10 Git Commands You'll Use Every Day (Beginner Friendly)" |
| `docker_commands.py` → `DockerCommands` | 10 lệnh: pull, images, run, ps, logs, exec, stop, rm, build, compose up. Hook: "It works on MY machine!" | Terminal + Docker Hub → Images → Containers; Bit chui vào container khi `exec`. Bản dài: mẹo + cheat sheet | "Image = recipe. Container = cake." | "Then we'll ship your machine. That's Docker!" | "10 DOCKER COMMANDS" | "10 Docker Commands Every Developer Needs (Image vs Container)" |

**Độ dài (render 2026-10-18, tất cả ĐẠT QC), 16:9 / 9:16:**

| Video | 16:9 | 9:16 |
|---|---|---|
| off_by_one | 1:13 | 1:11 |
| binary_search | 1:23 | 1:07 |
| aliasing | 1:11 | 1:03 |
| floating_point | 1:22 | 1:07 |
| hash_map | 1:24 | 1:07 |
| selection_sort | 1:47 | 1:09 |
| git_commands | 2:15 | 1:14 |
| docker_commands | 2:29 | 1:18 (cảnh báo > 75s) |

Bảng **số liệu sau khi đăng** cho mỗi video dùng cùng mẫu với Recursion ở trên. Ghi vào đây khi có số liệu.

## Thêm video mới

1. Tạo `<topic>.py`: `from bitbybit import *`, một class kế thừa `BitScene`. Mẫu gọn nhất là `off_by_one.py`, `aliasing.py`. Các hàm dựng sẵn trong `BitScene`:
   - `hook_open()` + `hook_visual()`: cold open của bản ngắn; `hook_look` làm cảnh nối vòng về khung đầu.
   - `title_intro()`: Bit gõ tiêu đề trên laptop.
   - `say()`: bong bóng thoại kèm lồng tiếng.
   - `console()` / `console_print()`: khung OUTPUT.
   - `make_code()`, `line_bar()`, `bar_to()`: khung code và thanh dòng đang chạy.
   - `hop()` / `stand()`: Bit nhảy hoặc đứng lên một điểm.
   - `joke()`: câu đùa kèm tiếng trống.
   - `error_banner()`: banner lỗi đỏ.
   - `shocked_bit()` / `knocked_bit()`: Bit hoảng hốt / Bit ngã mắt chữ X.
   - `ending()`: cảnh kết với tiêu đề câu chốt, thẻ kênh, Subscribe và cảnh nối vòng.
   - `discard()`: xoá hẳn một mobject. `Scene.remove()` không xoá các bộ phận đã bị animation tách ra; ví dụ Bit đã từng xoay tay.
2. Dùng `pick()` / `SHORT` ngay từ đầu cho mọi bố cục. Ở bản dọc, đặt Bit sao cho bong bóng thoại không che thứ đang được giải thích. Nếu cần, viết hàm `line()` riêng chọn hướng bong bóng theo tỉ lệ, như `aliasing.py` và `binary_search.py`.
3. Render xem nhanh bằng `-ql` ở cả hai tỉ lệ, rồi mới render `-qh`.
4. Gắn `self.chapter(...)` cho từng phần, `self.moment(...)` ở các khoảnh khắc chính, và `captioned=True` cho câu đọc có chữ trên màn hình. Bản ngắn kết bằng cảnh nối vòng (`loop`).
5. Làm thumbnail: `class Thumbnail(ThumbnailMixin, <Video>)` với `design()`. Khi người dùng muốn chọn, làm 2–3 phương án.
6. Duyệt kịch bản theo checklist độ thu hút (phần duyệt nội dung) trước khi render bản chính.
7. Đăng ký video trong `VIDEOS` của `qc.py`, chạy `qc.py --fix` tới khi ĐẠT, rồi duyệt ảnh lưới.
8. Thêm một mục mới vào phần **Cấu hình từng video** ở trên, kèm kết quả duyệt nội dung và bảng số liệu sau khi đăng.

## Cách làm việc với người dùng

- **Khi thay đổi thiết kế** (watermark, bố cục, hiệu ứng): render vài phương án thành ảnh để người dùng chọn, kèm đề xuất của mình.
- **File cho người dùng xem:** đặt trong project (ví dụ `media/...`), không để trong `/tmp`, và đưa link bấm được.
- **Commit:** chỉ commit khi người dùng yêu cầu.
- **Render nhiều video hoặc render lâu** (render lại tất cả, `qc.py --fix` cho nhiều video, bản -qh 1440p): không tự chạy. Đưa lệnh cho người dùng tự chạy khi họ muốn. Render thử `-ql` một video để kiểm tra thay đổi thì vẫn được.
