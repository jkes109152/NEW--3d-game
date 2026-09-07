CREATE TABLE `mp_members` (
	`room_id` text NOT NULL,
	`player_id` text NOT NULL,
	`ready` integer DEFAULT 0 NOT NULL,
	`profile` text,
	`input` text DEFAULT '{}' NOT NULL,
	`input_seq` integer DEFAULT 0 NOT NULL,
	`seen_at` integer NOT NULL,
	PRIMARY KEY(`room_id`, `player_id`)
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_mp_members_player` ON `mp_members` (`player_id`);--> statement-breakpoint
CREATE TABLE `mp_players` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`token_hash` text NOT NULL,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_mp_players_token` ON `mp_players` (`token_hash`);--> statement-breakpoint
CREATE TABLE `mp_results` (
	`run_id` text NOT NULL,
	`player_id` text NOT NULL,
	`profile_id` text NOT NULL,
	`rebirth` integer NOT NULL,
	`reward` integer NOT NULL,
	`party_size` integer NOT NULL,
	`level_a` integer NOT NULL,
	`level_b` integer NOT NULL,
	`campaign` integer NOT NULL,
	`created_at` integer NOT NULL,
	PRIMARY KEY(`run_id`, `player_id`)
);
--> statement-breakpoint
CREATE TABLE `mp_rooms` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`host_id` text NOT NULL,
	`status` text DEFAULT 'waiting' NOT NULL,
	`run_id` text,
	`level_a` integer DEFAULT 1 NOT NULL,
	`level_b` integer DEFAULT 1 NOT NULL,
	`campaign` integer DEFAULT 2 NOT NULL,
	`roster` text DEFAULT '[]' NOT NULL,
	`snapshot` text,
	`sequence` integer DEFAULT 0 NOT NULL,
	`updated_at` integer NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_mp_rooms_active` ON `mp_rooms` (`status`,`updated_at`);