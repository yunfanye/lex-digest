CREATE TABLE `lex_digest__checks` (
	`id` text PRIMARY KEY NOT NULL,
	`ran_at` integer NOT NULL,
	`status` text NOT NULL,
	`feed_count` integer,
	`new_count` integer,
	`summarized_count` integer,
	`note` text
);
--> statement-breakpoint
CREATE TABLE `lex_digest__episodes` (
	`guid` text PRIMARY KEY NOT NULL,
	`slug` text NOT NULL,
	`episode_number` integer,
	`title` text NOT NULL,
	`guest` text,
	`link` text NOT NULL,
	`transcript_url` text,
	`audio_url` text,
	`youtube_id` text,
	`pub_date` integer NOT NULL,
	`shownotes` text,
	`chapters` text,
	`status` text DEFAULT 'pending' NOT NULL,
	`summary_source` text,
	`error` text,
	`one_liner` text,
	`summary` text,
	`takeaways` text,
	`highlights` text,
	`topics` text,
	`transcript_chars` integer,
	`segment_count` integer,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	`summarized_at` integer
);
