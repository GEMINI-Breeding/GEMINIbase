# Trait Level API Example

This example demonstrates how to use the TraitLevel API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/trait_level_api.py`.

## Code

```python
from gemini.api.trait_level import TraitLevel

# Create a new trait leve
new_trait_level = TraitLevel.create(
    trait_level_name="Trait Level Test 1",
    trait_level_info={"test": "test"},
)
print(f"Created New Trait Level: {new_trait_level}")

# Get the trait level by name
trait_level = TraitLevel.get(trait_level_name="Trait Level Test 1")
print(f"Retrieved Trait Level: {trait_level}")

# Get the trait level by ID
trait_level_by_id = TraitLevel.get_by_id(id=new_trait_level.id)
print(f"Retrieved Trait Level by ID: {trait_level_by_id}")

# Get all trait levels
all_trait_levels = TraitLevel.get_all()
for trait_level in all_trait_levels:
    print(f"Trait Level: {trait_level}")

# Search Trait Levels
searched_trait_levels = TraitLevel.search(trait_level_name="Trait Level Test 1")
length_searched_trait_levels = len(searched_trait_levels)
print(f"Found {length_searched_trait_levels} trait levels with name 'Trait Level Test 1'")


# Update the trait level
trait_level.update(
    trait_level_info={"test": "test_updated"},
)
print(f"Updated Trait Level: {trait_level}")

# Set trait level info
trait_level.set_info(
    trait_level_info={"test": "test_set"},
)
print(f"Set Trait Level Info: {trait_level.get_info()}")

# Check if trait level exists before deletion
exists = TraitLevel.exists(
    trait_level_name="Trait Level Test 1",
)
print(f"Trait Level exists: {exists}")

# Delete the created trait level
is_deleted = trait_level.delete()
print(f"Deleted Trait Level: {is_deleted}")

# Check if trait level exists after deletion
exists_after_deletion = TraitLevel.exists(
    trait_level_name="Trait Level Test 1",
)
print(f"Trait Level exists after deletion: {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing trait levels using the GEMINIbase API:

*   **Creating a trait level:** The `TraitLevel.create()` method is used to create a new trait level with a name and additional information.
*   **Getting a trait level:** The `TraitLevel.get()` method retrieves a trait level by its name. The `TraitLevel.get_by_id()` method retrieves a trait level by its unique ID.
*   **Getting all trait levels:** The `TraitLevel.get_all()` method retrieves all trait levels in the database.
*   **Searching for trait levels:** The `TraitLevel.search()` method finds trait levels based on specified criteria, such as the name.
*   **Updating a trait level:** The `TraitLevel.update()` method updates the attributes of an existing trait level.
*   **Setting trait level information:** The `TraitLevel.set_info()` method updates the `trait_level_info` field with new data.
*   **Checking for existence:** The `TraitLevel.exists()` method verifies if a trait level with the given name exists.
*   **Deleting a trait level:** The `TraitLevel.delete()` method removes the trait level from the database.
