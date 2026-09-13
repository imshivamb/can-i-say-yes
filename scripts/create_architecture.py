from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "architecture" / "architecture.png"

AI = "#4f46e5"
DET = "#0f766e"
HUMAN = "#c2410c"
INK = "#18181b"
MUTED = "#52525b"
LINE = "#d4d4d8"
BG = "#fafafa"
WHITE = "#ffffff"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def panel(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    body: str,
    accent: str,
) -> None:
    left, top, right, bottom = xy
    draw.rounded_rectangle(xy, radius=16, fill=WHITE, outline=LINE, width=2)
    draw.rounded_rectangle((left, top, left + 8, bottom), radius=4, fill=accent)
    draw.text((left + 24, top + 16), title, fill=accent, font=font(22))
    draw.multiline_text((left + 24, top + 52), body, fill=INK, font=font(17), spacing=6)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((*start, *end), fill=MUTED, width=3)
    dx = 1 if end[0] >= start[0] else -1
    dy = 1 if end[1] >= start[1] else -1
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        draw.polygon(
            [end, (end[0] - 10 * dx, end[1] - 7), (end[0] - 10 * dx, end[1] + 7)],
            fill=MUTED,
        )
    else:
        draw.polygon(
            [end, (end[0] - 7, end[1] - 10 * dy), (end[0] + 7, end[1] - 10 * dy)],
            fill=MUTED,
        )


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1680, 1080), BG)
    draw = ImageDraw.Draw(image)
    draw.text((64, 36), "Can I Say Yes?", fill=INK, font=font(36))
    draw.text(
        (66, 86),
        "Plan B as deployed: Vercel UI · EC2 product API · Strands in-process · Bedrock Mantle",
        fill=MUTED,
        font=font(20),
    )
    draw.text((66, 118), "AI proposes  ·  deterministic code verifies  ·  a human approves writes", fill=MUTED, font=font(18))

    panel(draw, (64, 180, 360, 400), "PEOPLE + CHANNELS", "Rohan / Autopilot\nGmail inbound (port)\nCalendar evidence (port)\nSES outbound (port)", HUMAN)
    panel(
        draw,
        (400, 180, 860, 400),
        "PRODUCT SURFACE",
        "Next.js Autopilot on Vercel\nFastAPI on EC2 t3.micro\nShared file-backed demo world\nPress Reset first",
        DET,
    )
    panel(
        draw,
        (900, 180, 1280, 400),
        "AI  ·  STRANDS",
        "Investigator: evidence + feasibility\nMonitor: re-evaluate after change\nInvestigator as_tool handoff\nBedrock Mantle (GLM 4.7 Flash)",
        AI,
    )
    panel(
        draw,
        (1320, 180, 1616, 400),
        "HUMAN AUTHORITY",
        "Decision card\nApprove / reject\nSpend and promise only\nafter a human click",
        HUMAN,
    )
    panel(
        draw,
        (400, 460, 860, 720),
        "DETERMINISTIC ENGINE",
        "Schedule · capacity · conflicts\nFreshness · state machine\nPolicy engine\nAuthorityAndTraceHooks",
        DET,
    )
    panel(
        draw,
        (900, 460, 1280, 720),
        "WORLD",
        "data/ file fixtures\nNorthstar Creative seed\nDynamoDB/S3 ports defined,\nnot deployed",
        DET,
    )
    panel(
        draw,
        (1320, 460, 1616, 720),
        "AGENTCORE",
        "Same FastAPI container\n/invocations + /ping ready\nRuntime not hosting demo\nIn-process on EC2 today",
        AI,
    )

    arrow(draw, (360, 290), (400, 290))
    arrow(draw, (860, 290), (900, 290))
    arrow(draw, (1280, 290), (1320, 290))
    arrow(draw, (630, 400), (630, 460))
    arrow(draw, (1090, 400), (1090, 460))
    arrow(draw, (860, 590), (900, 590))

    draw.rounded_rectangle((64, 780, 1616, 1020), radius=16, fill=WHITE, outline=LINE, width=2)
    draw.text((88, 804), "What a judge should believe", fill=INK, font=font(22))
    draw.multiline_text(
        (88, 848),
        "Live loop: Reset → Check feasibility → Approve → Simulate supplier delay → Approve backup.\n"
        "Each live step calls a Strands agent on Bedrock. Dates and capacity are never computed by the model.\n"
        "Writes are policy-gated. The public API runs agents in-process; AgentCore is a passthrough when an ARN is set.\n"
        "App Runner is not used (paid-only on this account). Observability screenshot is optional until a runtime exists.",
        fill=INK,
        font=font(18),
        spacing=8,
    )
    image.save(OUTPUT)


if __name__ == "__main__":
    main()
