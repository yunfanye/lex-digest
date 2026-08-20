---
guid: "https://lexfridman.com/?p=4309"
slug: "sergey-levine"
episode: 108
title: "#108 – Sergey Levine: Robotics and Machine Learning"
guest: "Sergey Levine"
link: "https://lexfridman.com/sergey-levine/"
youtube_id: "kxi-_TT_-Nc"
published: "2020-07-14"
summary_source: "transcript"
summarized_at: "2026-08-19T20:30:00.000Z"
topics: ["data", "learning", "must", "learn", "levine", "robotics", "robots", "experience"]
---

# One-liner

Sergey Levine explains why robotics is a demanding test for machine learning: robots must gather experience in messy physical environments, learn useful representations, and turn imperfect objectives into reliable actions.

# Summary

A robot cannot cheaply collect unlimited perfectly labeled examples, so learning systems must make more use of unstructured interaction and reuse experience across tasks. Levine discusses systems that learn perception and control together, while stressing that success still depends on what data the robot sees and what behavior the objective rewards.

Physical robots make trial-and-error expensive, which pushes research toward offline data, transfer, model-based reasoning, and methods that can learn from fewer dangerous mistakes. The conversation notes that a learned controller can faithfully optimize a flawed target, making the choice of data and reward functions part of the engineering responsibility.

# Takeaways

## Robotics exposes the cost of bad data

A robot cannot cheaply collect unlimited perfectly labeled examples, so learning systems must make more use of unstructured interaction and reuse experience across tasks.

## End-to-end learning trades hand engineering for data and objectives

Levine discusses systems that learn perception and control together, while stressing that success still depends on what data the robot sees and what behavior the objective rewards.

## Reinforcement learning must become more data efficient

Physical robots make trial-and-error expensive, which pushes research toward offline data, transfer, model-based reasoning, and methods that can learn from fewer dangerous mistakes.

## Objective design carries ethical consequences

The conversation notes that a learned controller can faithfully optimize a flawed target, making the choice of data and reward functions part of the engineering responsibility.

# Highlights

## Conversation @ (00:03:05)

> There is a little video that I think robotics researchers really like to show, especially robotics learning researchers like myself, from 2004 from Stanford, which demonstrates a prototype robot called the PR1, and the PR1 was a robot that was designed as a home assistance robot.

Context: On robotics exposes the cost of bad data.

## Conversation @ (01:02:07)

> It's because when you try to actually do trial and error learning, reinforcement learning, directly in the real world where you have the potential to gather these large, highly

Context: On reinforcement learning must become more data efficient.

## Conversation @ (01:20:42)

> So classically, this is something that has been pretty hard in reinforcement learning because it's difficult for a designer to have good intuition about, you know, what a learning algorithm will come up with when they give it some objective.

Context: On end-to-end learning trades hand engineering for data and objectives.

## Conversation @ (01:24:50)

> I mean, machine learning systems have in some ways have revealed to us the ethical flaws in our data.

Context: On robotics exposes the cost of bad data.

## Conversation @ (01:37:14)

> The deep learning, machine learning, reinforcement learning has shown incredible results and breakthroughs and just inspired thousands, maybe millions of researchers.

Context: On reinforcement learning must become more data efficient.

# Chapters

- [00:00:00] Full conversation
