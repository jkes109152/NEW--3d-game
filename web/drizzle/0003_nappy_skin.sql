ALTER TABLE `mp_members` ADD `input_stream` text;--> statement-breakpoint
ALTER TABLE `mp_members` ADD `input_instance` text;--> statement-breakpoint
ALTER TABLE `mp_members` ADD `input_received_at` integer;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `mode` text DEFAULT 'coop' NOT NULL;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `roster_revision` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `starts_at` integer;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `time_limit_seconds` integer;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `host_instance_id` text;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `simulation_seen_at` integer;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `simulation_tick` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `result` text;--> statement-breakpoint
ALTER TABLE `mp_rooms` ADD `departures` text DEFAULT '{}' NOT NULL;