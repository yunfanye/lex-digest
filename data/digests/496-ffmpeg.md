---
guid: "https://lexfridman.com/?p=6450"
slug: "ffmpeg"
episode: 496
title: "#496 – FFmpeg: The Incredible Technology Behind Video on the Internet"
guest: "FFmpeg"
link: "https://lexfridman.com/ffmpeg/"
youtube_id: "nepKKz-MzFM"
published: "2026-05-06"
summary_source: "transcript"
summarized_at: "2026-08-18T05:43:57.000Z"
topics: ["FFmpeg","VLC","video codecs","open source licensing","reverse engineering","handwritten assembly","codec patents","maintainer burnout"]
---

# One-liner

The creators behind VLC and FFmpeg explain how the invisible open-source software running nearly all internet video actually works, and the volunteer culture, hand-written assembly, and ethical stands that built it.

# Summary

Jean-Baptiste Kempf (president of VideoLAN, creator of VLC) and Kieran Kunhya (FFmpeg contributor and the voice behind the FFmpeg Twitter/X account) join Lex to explain the technical machinery and the human story behind FFmpeg and VLC, two open-source projects that quietly underpin nearly all video on the internet — YouTube, Netflix, Chrome, Discord, OBS, and thousands of other platforms. They walk through the full pipeline of video playback: demuxing a container (MP4, MKV, MOV) into audio/video/subtitle tracks, decoding via codecs that exploit spatial and temporal redundancy (I/P/B frames, DCT transforms, YUV color space tuned to human perception), and finally rendering pixels and sound. Nearly every stage of that pipeline is someone's life's work: FFmpeg alone contains 100,000 hand-written assembly lines, and its VideoLAN-born AV1 decoder dav1d has 240,000 (79.9% of the codebase), built because the team refused to accept that "AV1 needs hardware to decode."

The conversation traces FFmpeg's history through eras — Fabrice Bellard's founding, Michael Niedermayer's Sisyphean 2000s work supporting endless DivX/Xvid/RealMedia variants, the rise of reverse-engineering legends like Kostya Shishkov (who reverse-engineered 20-30 megabyte proprietary binary blobs like GoToMeeting's codec purely by disassembly and intuition), and the assembly wizardry of Loren Merritt (x264), Henrik Gramner, and Martin Storsjö. They detail why handwritten assembly (SIMD, custom calling conventions, exploiting CPU pipelining) still beats compiler auto-vectorization by multiples, not percentages, and why that matters as Moore's Law slows. They also cover the codec/container distinction, the patent minefield behind H.264/HEVC/VVC licensing (which motivated Google/Netflix/Amazon to found the royalty-free Alliance for Open Media and create AV1/AV2), and open-source licensing mechanics (GPL vs LGPL vs MPL), including JB's years-long effort to re-license VLC by tracking down over 350 individual copyright holders.

The human side gets equal time. JB repeatedly turned down "dozens of millions of dollars" from ad/spyware companies to keep VLC clean, a decision now memed on Reddit; Kieran recounts the 2024 blowup with Google's AI-generated security reports (marked "critical" on obscure 1990s game codecs) and Microsoft Teams demanding enterprise SLA-level support from unpaid volunteers via the FFmpeg bug tracker (the "XZ fiasco" parallel), both of which eventually led to increased donations and improved corporate behavior. They discuss maintainer burnout as a bigger threat than internal drama (like the 2011 FFmpeg/Libav fork), JB's own experience with anonymous death threats over dropping PowerPC support, and being approached twice by intelligence agencies requesting VLC backdoors (he refused both times). The episode closes on where multimedia is headed — volumetric/point-cloud video, haptic and spatial-audio tracks, and eventually brain-computer-interface codecs — plus JB's new startup Kyber, an open-source (dual AGPL/commercial licensed) ultra-low-latency streaming stack aiming for four-millisecond glass-to-glass latency for teleoperating robots, drones, and remote machines.

# Takeaways

## Handwritten assembly still beats compiled C by multiples, not percentages

Kieran and JB argue that despite decades of compiler auto-vectorization improvements, hand-written SIMD assembly in FFmpeg and dav1d routinely outperforms C by 10x to 62x on specific functions, because engineers exploit CPU pipelining, custom calling conventions, and even repurpose unrelated instructions (e.g. cryptography instructions) in ways compilers never would.

## Video compression fools human perception rather than minimizing mathematical error

For 20 years the industry optimized codecs for peak signal-to-noise ratio (PSNR), a mathematical metric that led to blurry video. x264's breakthrough was psychovisual rate distortion and adaptive quantization — biasing bits toward what looks good to the human eye rather than what scores well mathematically — using the 'ParkJoy' and 'Planet Earth birds' test clips as the gold standard.

## Modern codecs (AV1, VVC) are collections of tools, not single algorithms

Each new-generation codec bundles many different coding tools (screen-share optimizations, animation tools, natural video tools) and dynamically switches between them depending on content, which is why encoding AV1 takes roughly two orders of magnitude more CPU than encoding H.264 for a similar quality gain of about 30% per generation.

## Video codec patents are a legal minefield that drove the creation of AV1/AV2

HEVC licensing fragmented into multiple competing patent pools (MPEG LA, HEVC Advance, and holdouts like Nokia) with uncapped fees that could cost YouTube or Netflix hundreds of millions of dollars a year, prompting Google, Netflix, Amazon and others to found the Alliance for Open Media and build royalty-free AV1/AV2 instead.

## Codec bit-exactness is a hard-won industry standard that MPEG-2 lacked

Since roughly the 2000s, video codec specifications require every compliant decoder implementation to produce identical output bit-for-bit; MPEG-2 in the early 1990s did not enforce this, which multimedia veterans consider one of the era's biggest standardization mistakes.

## Reverse-engineering proprietary codecs is closer to archaeology than programming

Engineers like Kostya Shishkov reverse-engineered 20-30 megabyte proprietary binary blobs (e.g. GoToMeeting's codec) with no documentation, stepping through disassemblers instruction by instruction, dumping raw YUV output for comparison, and inferring DCT/entropy-coding structure purely from binary patterns — work that can take a month per megabyte of binary.

## Maintainer burnout is a bigger threat than forks

Both guests argue that AI-generated security reports flooding volunteer bug trackers with false-urgency labels, and large companies treating free projects as paid vendors with SLAs, cause more psychological damage to unpaid maintainers than technical forks like the 2011 FFmpeg/Libav split, which was ultimately healthy and made FFmpeg stronger.

## Turning down money to preserve integrity paid off

JB Kempf refused repeated multi-million-dollar offers to bundle spyware, toolbars, or ads into VLC, reasoning that compromising trust would eventually destroy the project (via forks or user abandonment) even if it generated short-term revenue — a decision credited with helping VLC reach 6.5+ billion downloads.

# Highlights

## Jean-Baptiste Kempf @ (00:00:00)

> The important thing is, is your code good? We care about excellent code. We don’t care who you are. Like maybe you’re a dog. I don’t care, right? I don’t care where you come from. I need to look at your code.

Context: On FFmpeg/VLC's purely merit-based contribution culture

## Jean-Baptiste Kempf @ (00:00:45)

> FFmpeg has one hundred thousand lines of assembly for all the codecs.

Context: Contrasting FFmpeg's total assembly footprint with dav1d's 240,000 lines alone

## Jean-Baptiste Kempf @ (00:01:41)

> The intelligence agencies tried to, like, say, 'Can you put a backdoor in VLC?' ... No. Well, I was a lot less polite. ... if we had to compromise our software, we would shut it down. This is clear.

Context: Recounting being approached twice by government agencies asking for a VLC backdoor

## Jean-Baptiste Kempf @ (02:29:58)

> It is an order of magnitude easier to write code than read code.

Context: Explaining why rewriting mature codebases (e.g. in Rust) is far harder than it looks

## Jean-Baptiste Kempf @ (02:07:56)

> We are talking about 30,000 lines of C, but 240,000 lines of handwritten assembly, right?

Context: Describing the scale of the dav1d AV1 decoder, built because AV1 was assumed to need hardware

## Jean-Baptiste Kempf @ (02:44:36)

> To give you an idea, I received death threats on VideoLAN, right?

Context: Recounting being sent a powder-laced threat letter after dropping PowerPC support in VLC around 2009-2010

## Kieran Kunhya @ (04:13:53)

> Talk is cheap, send patches.

Context: Naming his favorite FFmpeg tweet, summarizing the project's ethos

# Chapters

- [00:00:00] Episode highlight
- [00:02:17] Introduction
- [00:05:35] Weirdest things VLC opens
- [00:09:59] How video playback works
- [00:19:20] Video codecs and containers
- [00:30:06] FFmpeg explained
- [00:51:07] Linus Torvalds
- [00:55:46] Turning down millions to keep VLC ad-free
- [01:10:01] FFmpeg & Google drama
- [01:29:19] FFmpeg developers
- [01:35:56] VLC and FFmpeg
- [01:40:15] History of FFmpeg
- [01:43:45] Reverse engineering codecs
- [01:57:01] FFmpeg testing
- [02:01:04] Assembly code (handwritten)
- [02:25:27] Rust programming language
- [02:34:43] FFmpeg and Libav fork
- [02:43:02] Open source burnout
- [02:50:51] x264 and internet video
- [03:04:06] Video compression basics
- [03:11:04] CIA and fake VLC
- [03:21:40] Ultra low latency streaming
- [03:38:57] AV2 codec and video patents
- [03:49:00] VLC backdoors
- [03:59:14] Video archiving
- [04:05:52] Future of FFmpeg and VLC
