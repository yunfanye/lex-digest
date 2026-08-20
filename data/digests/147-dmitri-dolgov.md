---
guid: "https://lexfridman.com/?p=4474"
slug: "dmitri-dolgov"
episode: 147
title: "#147 – Dmitri Dolgov: Waymo and the Future of Self-Driving Cars"
guest: "Dmitri Dolgov"
link: "https://lexfridman.com/dmitri-dolgov/"
youtube_id: "P6prRXkI5HM"
published: "2020-12-20"
summary_source: "transcript"
summarized_at: "2026-08-19T20:30:00.000Z"
topics: ["maps", "learning", "dolgov", "autonomous", "driving", "perception", "prediction", "planning"]
---

# One-liner

Dmitri Dolgov explains Waymo's approach to autonomous driving, covering perception, maps, prediction, planning, machine learning, simulation, trucking, and the engineering tradeoffs between modular systems and more end-to-end learning.

# Summary

Perception, localization, prediction, and planning are separable engineering problems, yet an error or uncertainty in one layer changes what the others should do. Detailed maps can encode stable road geometry and traffic rules, letting the online system devote more capacity to dynamic objects and unexpected conditions.

Dolgov describes a stack with many learned components while preserving interfaces that make behavior testable, debuggable, and easier to reason about during safety work. Highway-heavy routes, vehicle dynamics, depot operations, and commercial utilization create a different deployment problem from a passenger robotaxi even when much of the autonomy technology is shared.

# Takeaways

## Autonomous driving depends on a tightly coupled stack

Perception, localization, prediction, and planning are separable engineering problems, yet an error or uncertainty in one layer changes what the others should do.

## Maps provide prior structure while sensors handle change

Detailed maps can encode stable road geometry and traffic rules, letting the online system devote more capacity to dynamic objects and unexpected conditions.

## Machine learning and modularity are not opposites

Dolgov describes a stack with many learned components while preserving interfaces that make behavior testable, debuggable, and easier to reason about during safety work.

## Trucking changes the operating environment and economics

Highway-heavy routes, vehicle dynamics, depot operations, and commercial utilization create a different deployment problem from a passenger robotaxi even when much of the autonomy technology is shared.

# Highlights

## Conversation @ (00:09:22)

> That was after grad school, uh, after, and I actually, the most self driving cars was I think my first real hands on introduction to robotics.

Context: On autonomous driving depends on a tightly coupled stack.

## Conversation @ (01:18:47)

> can mention at least briefly, you know, Waymo is also now doing autonomous trucking and how different like philosophically and technically is that whole space of problems.

Context: On autonomous driving depends on a tightly coupled stack.

## Conversation @ (01:45:48)

> There's, you know, really good ways it gets into some fairly complex design choices where on one hand you want modularity and decomposability, decomposability of your system.

Context: On maps provide prior structure while sensors handle change.

## Conversation @ (02:00:15)

> The stakes are high, in a sense, but it's also beautiful that for somebody who loves artificial intelligence, the possibility that an AI system might be able to save a human life.

Context: On maps provide prior structure while sensors handle change.

## Conversation @ (02:22:55)

> There's lighters are almost exclusively in house and some of the technologies that we have, some of the fundamental technologies there are completely unique to Waymo.

Context: On autonomous driving depends on a tightly coupled stack.

# Chapters

- [00:00:00] Full conversation
