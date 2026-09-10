from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "architecture" / "architecture.png"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str, body: str) -> None:
    draw.rounded_rectangle(xy, radius=18, fill="#ffffff", outline="#cbd8d2", width=3)
    left, top, right, _ = xy
    draw.text((left + 22, top + 18), title, fill="#0d684f", font=font(25))
    draw.multiline_text((left + 22, top + 58), body, fill="#1c2924", font=font(18), spacing=7)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((*start, *end), fill="#0d684f", width=5)
    draw.polygon(
        [end, (end[0] - 12, end[1] - 8), (end[0] - 12, end[1] + 8)],
        fill="#0d684f",
    )


def main() -> None:
    image = Image.new("RGB", (1600, 1000), "#f4f7f4")
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "Can I Say Yes? · production path", fill="#18201d", font=font(38))
    draw.text(
        (72, 98),
        "AI proposes → deterministic domain verifies → policy protects human authority",
        fill="#68736f",
        font=font(21),
    )

    box(draw, (70, 190, 390, 370), "INPUT", "Gmail request\nAutopilot UI\nSupplier email")
    box(
        draw,
        (470, 160, 830, 400),
        "STRANDS",
        "Investigator\nEvidence + feasibility\nMonitor\nBackground re-evaluation",
    )
    box(
        draw,
        (910, 190, 1260, 370),
        "TOOLS + DATA",
        "Google Calendar\nFile fixtures\nDomain scheduler\nEvidence store",
    )
    box(
        draw,
        (470, 540, 830, 760),
        "GUARDRAILS",
        "Deterministic conflicts\nFreshness + policy\nStrands authority hook\nAudit trail",
    )
    box(
        draw,
        (910, 540, 1260, 760),
        "HUMAN",
        "Decision card\nApprove / reject\nOnly consequential writes",
    )
    box(
        draw,
        (1340, 330, 1530, 600),
        "OUTPUT",
        "SES reply\nCommitment state\nAT RISK escalation\nCloudWatch trace",
    )

    arrow(draw, (390, 280), (470, 280))
    arrow(draw, (830, 280), (910, 280))
    arrow(draw, (650, 400), (650, 540))
    arrow(draw, (830, 650), (910, 650))
    arrow(draw, (1260, 650), (1340, 500))
    arrow(draw, (1260, 280), (1340, 410))
    image.save(OUTPUT)


if __name__ == "__main__":
    main()
