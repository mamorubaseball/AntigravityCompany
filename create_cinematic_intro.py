import os
from moviepy import VideoFileClip, ColorClip, CompositeVideoClip, ImageClip
import moviepy.video.fx as vfx
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Paths
INPUT_VIDEO = "/Users/mamoru/techmoney/マーベル+20260412/intro.mp4"
OUTPUT_VIDEO = "/Users/mamoru/techmoney/マーベル+20260412/intro_cinematic.mp4"
FONT_PATH = "/System/Library/Fonts/Supplemental/Futura.ttc" # Common Mac cinematic font

def create_text_image(text, size, font_size, color=(255, 255, 255), opacity=255):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    
    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # Draw centered
    draw.text(((size[0] - w) / 2, (size[1] - h) / 2), text, font=font, fill=(color[0], color[1], color[2], opacity))
    return np.array(img)

def main():
    print(f"Loading video: {INPUT_VIDEO}")
    clip = VideoFileClip(INPUT_VIDEO)
    w, h = clip.size
    
    # 1. Cinematic Aspect Ratio (2.35:1)
    # Target height for 1854 width is ~789
    target_ratio = 2.35
    target_h = int(w / target_ratio)
    bar_h = (h - target_h) // 2
    
    # Create black bars
    top_bar = ColorClip(size=(w, bar_h), color=(0, 0, 0)).with_duration(clip.duration)
    bottom_bar = ColorClip(size=(w, bar_h), color=(0, 0, 0)).with_duration(clip.duration).with_position(("center", "bottom"))
    
    # 2. Color Grading
    # Increase contrast and slight teal tint
    def color_grade(clip):
        # MoviePy 2.x transform approach
        def filter_func(get_frame, t):
            im = get_frame(t)
            # Contrast boost
            im = im.astype(float)
            im = (im - 128) * 1.2 + 128
            # Teal tint (Shadows)
            im[:, :, 2] *= 1.1 # Blue
            im[:, :, 1] *= 1.05 # Green
            im[:, :, 0] *= 0.85 # Red (Reduce more for stronger effect)
            return np.clip(im, 0, 255).astype('uint8')
        return clip.transform(filter_func)


    clip_graded = color_grade(clip)
    
    # 3. Text Overlays
    # Opening: "A STRATEGIC ANALYSIS"
    opening_text_img = create_text_image("A MARVELL STRATEGIC ANALYSIS", (w, h), 40)
    opening_text = (ImageClip(opening_text_img)
                   .with_duration(3)
                   .with_start(0)
                   .with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(1)]))
    
    # Title: "MARVELL: THE AI POWERHOUSE"
    title_text_img = create_text_image("MARVELL: THE AI POWERHOUSE", (w, h), 80)
    title_text = (ImageClip(title_text_img)
                 .with_duration(5)
                 .with_start(4)
                 .with_effects([vfx.CrossFadeIn(1.5), vfx.CrossFadeOut(1.5)]))
    
    # Metadata: "APRIL 2026"
    meta_text_img = create_text_image("APRIL 2026 | RESEARCH DEPT", (w, h), 25)
    meta_text = (ImageClip(meta_text_img)
                .with_duration(4)
                .with_start(clip.duration - 5)
                .with_position(("center", "bottom"))
                .with_effects([vfx.CrossFadeIn(1)]))

    # 4. Compose
    final = CompositeVideoClip([
        clip_graded,
        top_bar,
        bottom_bar,
        opening_text,
        title_text,
        meta_text
    ])
    
    print(f"Rendering cinematic intro to: {OUTPUT_VIDEO}")
    # Using low bitrate for testing/preview if needed, or high for quality
    final.write_videofile(OUTPUT_VIDEO, codec="libx264", audio_codec="aac", fps=clip.fps)
    
    print("Done!")

if __name__ == "__main__":
    main()
