---
guid: "https://lexfridman.com/?p=4415"
slug: "chris-lattner-2"
episode: 131
title: "#131 – Chris Lattner: The Future of Computing and Programming Languages"
guest: "Chris Lattner"
link: "https://lexfridman.com/chris-lattner-2/"
youtube_id: "nWTvXbQHwWs"
published: "2020-10-19"
summary_source: "transcript"
summarized_at: "2026-08-19T20:30:00.000Z"
topics: ["design", "language", "lattner", "swift", "llvm", "compiler", "hardware", "accelerators"]
---

# One-liner

Chris Lattner discusses Swift, LLVM, compiler design, hardware accelerators, and the craft of programming languages, focusing on how abstractions can give developers expressive code without hiding the performance model they eventually depend on.

# Summary

A reusable compiler infrastructure lets many front ends share optimization and code generation, lowering the cost of building a serious new language. Lattner describes choices around types, memory, generics, and compilation that aim to make common mistakes harder without giving up native execution.

ASICs and machine-learning accelerators create architectures whose parallelism and memory systems do not map cleanly onto assumptions inherited from general-purpose CPUs. Compilers, debuggers, package systems, diagnostics, libraries, interoperability, and migration paths determine whether an elegant design becomes a usable platform.

# Takeaways

## LLVM separated language design from machine-code backends

A reusable compiler infrastructure lets many front ends share optimization and code generation, lowering the cost of building a serious new language.

## Swift tries to combine safety with systems-level performance

Lattner describes choices around types, memory, generics, and compilation that aim to make common mistakes harder without giving up native execution.

## Hardware specialization changes what compilers must understand

ASICs and machine-learning accelerators create architectures whose parallelism and memory systems do not map cleanly onto assumptions inherited from general-purpose CPUs.

## A language succeeds through tooling and community as well as syntax

Compilers, debuggers, package systems, diagnostics, libraries, interoperability, and migration paths determine whether an elegant design becomes a usable platform.

# Highlights

## Conversation @ (00:08:14)

> No, why do we care about programming language design, creating effective programming languages, choosing one programming languages such as another programming language, why we keep struggling and improving through the evolution of these programming languages.

Context: On llvm separated language design from machine-code backends.

## Conversation @ (01:08:10)

> So if we project into the future, it's very possible that the number of these kinds of ASICs, very specific infrastructure architecture things like multiplies exponentially.

Context: On llvm separated language design from machine-code backends.

## Conversation @ (01:59:25)

> And so being able to have that is really the design in programming language design, and design is really, really hard.

Context: On llvm separated language design from machine-code backends.

## Conversation @ (02:15:44)

> And so programming paradigms, when you look across demands, is structured programming where you go from go tos to if, then, else, or functional programming from Lisp.

Context: On llvm separated language design from machine-code backends.

## Conversation @ (02:42:16)

> And so one of the fun things about learning programming languages, even maybe Lisp, I don't know if you agree with this, is that when you start doing that, you start learning new things.

Context: On llvm separated language design from machine-code backends.

# Chapters

- [00:00:00] Full conversation
