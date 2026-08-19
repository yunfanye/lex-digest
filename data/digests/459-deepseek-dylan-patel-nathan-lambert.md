---
guid: "https://lexfridman.com/?p=6155"
slug: "deepseek-dylan-patel-nathan-lambert"
episode: 459
title: "#459 – DeepSeek, China, OpenAI, NVIDIA, xAI, TSMC, Stargate, and AI Megaclusters"
guest: "DeepSeek, China, OpenAI, NVIDIA, xAI, TSMC, Stargate, and AI Megaclusters"
link: "https://lexfridman.com/deepseek-dylan-patel-nathan-lambert/"
youtube_id: "_1f-o0nqpEI"
published: "2025-02-03"
summary_source: "transcript"
summarized_at: "2026-08-19T17:30:00.000Z"
topics: ["DeepSeek", "DeepSeek R1", "China AI", "reinforcement learning", "open-weight models", "NVIDIA", "export controls", "AI compute"]
---

# One-liner

Dylan Patel and Nathan Lambert explain how DeepSeek R1 combined efficient engineering, open weights, and reinforcement learning to reset assumptions about model cost, Chinese AI capability, and the US chip strategy.

# Summary

Dylan Patel of SemiAnalysis and Nathan Lambert of the Allen Institute for AI unpack DeepSeek V3 and R1 at the level of chips, architecture, training, and product strategy. DeepSeek used a mixture-of-experts model, efficient communication, lower-precision arithmetic, strong data work, and a large reinforcement-learning stage to produce reasoning performance competitive with leading Western systems. The visible result challenged a simple equation between frontier quality and the largest possible American cluster.

The widely repeated training-cost figure receives careful qualification. Roughly $5.5 million referred to one reported final training run for V3 under particular accounting assumptions; it did not include earlier experiments, failed runs, data, salaries, inference, hardware acquisition, or the broader research program. DeepSeek still demonstrated real efficiency. Its achievement means that algorithmic and systems improvements can turn a restricted compute base into more capability, while frontier labs may use the same methods to spend even more effectively rather than stop scaling.

The panel debates US export controls, NVIDIA GPUs, smuggling, Huawei, TSMC, Taiwan, and China's manufacturing depth. Patel argues that controls can slow the construction of the largest clusters and preserve a US lead, though enforcement gaps and domestic Chinese innovation reduce their effect over time. Lambert emphasizes the scientific value of open weights and the speed with which the global research community can study, distill, and adapt a released model. DeepSeek's built-in political censorship remains distinct from the technical openness of its weights.

R1 also clarifies the emerging role of reinforcement learning for reasoning. Models can generate and verify long chains of work in coding, mathematics, and other domains with checkable outcomes, although they remain vulnerable to reward hacking and weak evaluators. The final sections cover allegations that Chinese labs trained on OpenAI outputs, NVIDIA's market reaction, AI agents, megaclusters, Stargate, and the likely convergence of open and closed systems. The durable lesson is competitive: cost curves fall, methods diffuse, and neither a hardware lead nor a single model release settles the race.

# Takeaways

## Reported cost is an accounting slice

A final training run does not equal total model-development cost. Comparisons should state whether they include research experiments, hardware depreciation, labor, data, and inference.

## Efficiency and scale compound

Techniques that let DeepSeek do more with fewer chips can also let a larger lab do much more with a giant cluster. Efficiency does not imply the end of capital spending.

## Reasoning RL needs verifiable rewards

Math and code offer tests that can score candidate solutions at scale. Open-ended research, politics, and human preference lack equally reliable judges.

## Open weights accelerate imitation and study

Researchers can inspect behavior, run local evaluations, fine-tune, distill, and build products without the original provider. The same access can spread misuse and embedded censorship patterns.

## Export controls buy time, not certainty

Restrictions can raise cluster cost and delay access to leading chips, while smuggling, stockpiles, domestic substitutes, and better software gradually reduce the gap.

## The AI race has several bottlenecks

Chips, power, networking, memory, fabrication, algorithms, data, talent, and deployment all matter. Dominance in one layer does not guarantee leadership across the stack.

# Highlights

## Nathan Lambert @ 00:06:17

> There’s not full agreement in the community, but for us that means releasing the training data, releasing the training code, and then also having open weights like this.

## Dylan Patel @ 00:27:07

> Versus again, the Llama model, 70 billion parameters must be activated or 405 billion parameters must be activated, so you’ve dramatically reduced your compute cost when you’re doing training and inference with this mixture of experts architecture.

## Nathan Lambert @ 00:56:33

> Accepted practice is that for any given model that is a notable advancement, you’re going to do two to 4x compute of the full training run in experiments alone.

## Nathan Lambert @ 01:02:25

> A large part of export controls, if they work is just that the amount of AI that can be run in China is going to be much lower.

## Dylan Patel @ 01:20:02

> Now, even on the compute side, when we look at chips versus data centers, China has the unprecedented ability to build ridiculous sums of power.

## Dylan Patel @ 03:31:00

> Actually, over the last couple of days, we’ve seen a lot of people distill DeepSeek’s model into Llama models, because the DeepSeek models are complicated to run inference on because they’re mixture of experts and they’re 600 plus billion parameters and all of this.

# Chapters

- [00:00:00] Preamble
- [00:03:33] DeepSeek-R1 and DeepSeek-V3
- [00:25:16] Low cost of training
- [00:51:30] DeepSeek compute cluster
- [00:58:58] Export controls on GPUs to China
- [01:09:16] AGI timeline
- [01:18:56] China’s manufacturing capacity
- [01:26:36] Cold war with China
- [01:31:06] TSMC and Taiwan
- [01:54:44] Best GPUs for AI
- [02:09:36] Why DeepSeek is so cheap
- [02:22:55] Espionage
- [02:31:58] Censorship
- [02:44:52] Andrej Karpathy and magic of RL
- [02:55:23] OpenAI o3-mini vs DeepSeek r1
- [03:14:31] NVIDIA
- [03:18:53] GPU smuggling
- [03:25:42] DeepSeek training on OpenAI data
- [03:36:00] AI megaclusters
- [04:11:27] Who wins the race to AGI?
- [04:21:39] AI agents
- [04:30:22] Programming and AI
- [04:37:58] Open source
- [04:47:01] Stargate
- [04:54:31] Future of AI
