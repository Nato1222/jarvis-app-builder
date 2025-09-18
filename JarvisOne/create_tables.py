from .database.create_tables import create_tables as _create

def create_tables():
	"""Delegate to database.create_tables.create_tables."""
	return _create()

if __name__ == "__main__":
	create_tables()
