import { seedInternalUser } from "./internal-auth";

/** Internal credentials are fixture-only until username Admin creation ships in #112. */
export async function provisionUser(email: string, password: string): Promise<void> {
  seedInternalUser(email, password);
}
