"""Clear Aura and re-seed logistics + Supabase profile sync."""

from aura_graphdb.aura_clear import clear_aura_graph
from aura_graphdb.aura_constraints import create_aura_constraints
from aura_graphdb.aura_seed_logistics import seed_aura_logistics


def reseed_aura():
    print("Clearing Aura graph...")
    clear_aura_graph()

    print("Creating Aura constraints...")
    create_aura_constraints()

    print("Seeding logistics data and syncing Supabase profiles...")
    seed_aura_logistics()

    print("Aura reseed completed.")


if __name__ == "__main__":
    reseed_aura()
