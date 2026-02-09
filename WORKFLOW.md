# Stoic Content Daily Production Workflow

## Brand Identity

**The Inner Citadel** | @theinnercitadel | Direct Marcus Aurelius reference, niche-savvy |
---

## Platform Strategy

| Platform | Priority | Aspect Ratio | Max Length | Posting Window (EST) |
|----------|----------|--------------|------------|---------------------|
| TikTok | PRIMARY | 9:16 | 10 min | 7-9 AM, 12-2 PM, 6-9 PM |
| Instagram Reels | PRIMARY | 9:16 | 90 sec | 8-10 AM, 1-3 PM, 7-9 PM |
| Facebook Reels | SECONDARY | 9:16 | 90 sec | Cross-post from IG |
| X (Video) | SECONDARY | 9:16 or 16:9 | 2 min 20 sec | Cross-post from TikTok |
| YouTube Shorts | SECONDARY | 9:16 | 60 sec | Cross-post from TikTok |

---

## Daily Video Series (12 Videos/Day)

### Batch A -- Morning Drop (4 videos, post 7-9 AM)
| # | Series | Format | Duration |
|---|--------|--------|----------|
| 1 | **Morning Stoic** | Quote + calm interpretation + sunrise/nature visuals | 60-75 sec |
| 2 | **Marcus Aurelius Said...** | Single emperor quote + historical context + statue visuals | 60-70 sec |
| 3 | **Stoic Thought of the Day** | Text-heavy quote card + ambient music + slow pan visuals | 60 sec |
| 4 | **Wake Up, Warrior** | Aggressive motivational cut + dramatic visuals + intense music | 65-75 sec |

### Batch B -- Midday Drop (4 videos, post 12-2 PM)
| # | Series | Format | Duration |
|---|--------|--------|----------|
| 5 | **Stoic Response To...** | Modern problem + stoic answer + split-screen ancient/modern | 65-80 sec |
| 6 | **One Quote That Changes Everything** | Dramatic hook + single powerful quote + cinematic buildup | 60-70 sec |
| 7 | **Seneca's Letters** | Read excerpt from a letter + parchment/library visuals | 60-75 sec |
| 8 | **Ancient Wisdom in 60 Seconds** | Broader philosophy (Aristotle, Lao Tzu, Buddha mixed in) | 60 sec |

### Batch C -- Evening Drop (4 videos, post 6-9 PM)
| # | Series | Format | Duration |
|---|--------|--------|----------|
| 9 | **Stoic vs. Modern** | Contrast ancient advice with modern culture + debate format | 65-80 sec |
| 10 | **Before You Sleep** | Calm nighttime reflection + dark/moody visuals + soft voice | 60-70 sec |
| 11 | **The Obstacle Is The Way** | Specific life challenge + stoic framework for handling it | 65-75 sec |
| 12 | **Silent Stoic** | NO voiceover -- text-only quote montage + cinematic music | 60 sec |

---

## Credit Budget Strategy (6,000 credits/month)

### The 60/40 Rule
- **60% Higgsfield clips** (~36 sec per video): 2-3 unique AI-generated clips
- **40% reusable/text/transition** (~24+ sec per video): text overlay screens, reused clip library, fade transitions

### Credit Math
- Average Higgsfield clip: 10 sec = ~3-4 segments @ 3 sec each
- Credits per clip (using DOP Lite/Turbo): ~4-6 credits
- Clips per video: 2-3 unique + 1-2 reused from library
- **Unique clips per video: ~2.5 average**
- Daily: 12 videos x 2.5 clips = 30 new clip generations
- Monthly: 30 x 30 = 900 generations
- Credits: 900 x ~5 avg = **~4,500 credits/month** (75% of budget)
- **Buffer: 1,500 credits** for retakes, experiments, and scaling

### Clip Library Strategy
Build a reusable visual library in `assets/clips/` organized by mood:
```
clips/
  serene/        -- sunrises, calm water, meadows
  dramatic/      -- storms, crashing waves, fire
  classical/     -- marble statues, columns, Roman ruins
  dark-moody/    -- rain on stone, candlelight, shadows
  modern/        -- city streets, gym, boardroom
  nature/        -- mountains, forests, ocean
  text-bg/       -- plain textured backgrounds for quote cards
```

**Week 1 Goal:** Generate 50 "evergreen" clips that can be reused across 30%+ of future videos.

---

## Daily Production Timeline

### Phase 1: Script Generation (30 min) -- 6:00 AM
1. Run `scripts/generate_daily_scripts.py` to produce 12 scripts from quote database
2. Review scripts for accuracy, tone, and variety
3. Approve or regenerate any that feel weak

### Phase 2: Voiceover Generation (45 min) -- 6:30 AM
1. Feed approved scripts to ElevenLabs
2. Use two voice profiles:
   - **Voice A (Calm/Deep):** Morning Stoic, Thought of the Day, Before You Sleep, Seneca's Letters
   - **Voice B (Intense/Commanding):** Wake Up Warrior, Stoic vs Modern, One Quote, The Obstacle
3. Export as WAV, store in `assets/audio/YYYY-MM-DD/`
4. **Silent Stoic series:** Skip voiceover, music only

### Phase 3: Visual Generation (90 min) -- 7:15 AM
1. Run `scripts/generate_visuals.py` to create Higgsfield prompts for each video
2. Generate 25-30 new clips in Higgsfield (batch the prompts)
3. Pull 10-15 reusable clips from library
4. Download all clips to `assets/clips/YYYY-MM-DD/`

### Phase 4: Assembly & Editing (120 min) -- 8:45 AM
1. Open CapCut (or Premiere)
2. For each video:
   - Import voiceover + clips
   - Arrange clips to match script flow
   - Add text overlays (quote text, series title, CTA)
   - Add background music track
   - Add brand watermark (small, corner)
   - Color grade for consistency
3. Export all 12 as 9:16 MP4 at 1080x1920
4. Save to `output/finals/YYYY-MM-DD/`

### Phase 5: Quality Control (30 min) -- 10:45 AM
1. Run `scripts/quality_check.py` against each video:
   - Duration >= 60 sec
   - Audio levels normalized
   - No Higgsfield watermarks visible (if applicable)
   - Text readable at mobile resolution
   - Brand watermark present
   - No duplicate clips from yesterday
2. Fix any failures, re-export

### Phase 6: Scheduling & Upload (30 min) -- 11:15 AM
1. Upload Batch A (videos 1-4) -- schedule for afternoon/evening if morning has passed
2. Upload Batch B (videos 5-8) -- schedule for midday slot
3. Upload Batch C (videos 9-12) -- schedule for evening slot
4. Add captions, hashtags, and CTAs from `scripts/generate_captions.py`
5. Cross-post secondaries to Facebook, X, YouTube Shorts

### Phase 7: Analytics & Iteration (15 min) -- Next Day 5:45 AM
1. Review previous day's performance in `logs/`
2. Note top 3 performers and bottom 3
3. Adjust next day's content mix based on what hit

---

## Total Daily Time Investment: ~5-6 hours

This decreases to ~3-4 hours by Week 2 as:
- Clip library reduces generation needs
- CapCut templates speed up assembly
- Batch workflows become muscle memory

---

## Hashtag Strategy

### Core (use on every post)
```
#stoicism #stoic #marcusaurelius #philosophy #wisdom
#mindset #motivation #selfimprovement #mentalhealth
```

### Rotating (mix 3-5 per post)
```
#seneca #epictetus #meditations #stoicquotes #ancientwisdom
#innerpeace #discipline #resilience #growthmindset #lifestyle
#deepthoughts #lifelessons #mindfulness #perspective #truth
```

### Platform-Specific
- **TikTok:** Add trending sounds/tags when relevant
- **Instagram:** Max 30 hashtags, mix sizes (large + niche)
- **X:** 2-3 hashtags max, focus on discoverability

---

## Week 1 Success Metrics

| Metric | Target |
|--------|--------|
| Videos published | 84 (12/day x 7 days) |
| Higgsfield credits used | < 1,500 (25% of monthly) |
| Clip library size | 50+ reusable clips |
| Avg watch time | > 40% of video length |
| Follower growth | Baseline established |
| Top performing series | Identified for Week 2 doubling |
