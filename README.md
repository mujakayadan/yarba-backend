# Resume Builder

A modern resume and cover letter builder with LaTeX output, powered by FastAPI, MongoDB, and Beanie ODM.

## Features

- Create and manage resumes and cover letters
- Generate professional LaTeX documents
- AI-powered content generation
- User authentication and authorization
- Responsive Streamlit UI

## Architecture

This application follows a clean architecture pattern with clear separation of concerns:

- **API Layer**: FastAPI routes and schemas
- **Core Layer**: Business logic and domain models
- **Database Layer**: MongoDB with Beanie ODM
- **UI Layer**: Streamlit interface

## Getting Started

### Prerequisites

- Python 3.10+
- Poetry
- MongoDB

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/resume-builder.git
cd resume-builder
```

2. Install dependencies:

```bash
poetry install
```

3. Set up environment variables:

Create a `.env` file in the project root with the following variables:

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=user_information
JWT_SECRET_KEY=your-secret-key
```

### Running the Application

1. Start the API server:

```bash
poetry run uvicorn api.main:app --reload
```

2. Start the Streamlit UI:

```bash
poetry run streamlit run ui/streamlit_app.py
```

## Database Migrations

This project uses Beanie's built-in migration system:

```bash
poetry run python -m scripts.run_migrations
```

## Testing

```bash
poetry run pytest
```

## License

MIT 

# Resume Builder MongoDB Improvements

This project contains improvements to the MongoDB data model for the Resume Builder application. The improvements focus on better relationships between collections, proper references, and a more structured approach to data storage.

## Entity Relationship Diagram

The entity relationship diagram can be found in the `design/entity_relationship.md` file. It shows the relationships between the different collections in the MongoDB database.

## Model Improvements

The following improvements have been made to the models:

1. **User Model**:
   - Added helper methods to get related documents (profile, portfolio, resumes)
   - Improved user preferences structure
   - Added additional fields for account management

2. **Profile Model**:
   - Added proper references to the user document
   - Added migration method for personal information
   - Added helper method to get related portfolio

3. **Portfolio Model**:
   - Separated portfolio items into their own collection
   - Added proper references to user and profile documents
   - Added helper methods to get portfolio items by type, tag, etc.

4. **Resume Model**:
   - Added proper references to user and portfolio documents
   - Added support for custom sections
   - Added helper method to get related portfolio

## Migration Scripts

Two migration scripts have been provided to help with the transition to the new data model:

1. **update_mongodb_references.py**:
   - Updates references between documents
   - Ensures consistent user_id references
   - Updates timestamps for consistency

2. **migrate_data.py**:
   - Extracts portfolio items from portfolios and creates separate documents
   - Updates references between collections
   - Migrates personal information from profiles to the new structure
   - Updates timestamps for consistency

## Running the Migration Scripts

To run the migration scripts, follow these steps:

1. Make sure MongoDB is running:
   ```powershell
   & "C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe"
   ```

2. Run the update_mongodb_references.py script:
   ```powershell
   python scripts/update_mongodb_references.py
   ```

3. Run the migrate_data.py script:
   ```powershell
   python scripts/migrate_data.py
   ```

## Benefits of the New Structure

The new structure provides the following benefits:

1. **Better Relationships**: Proper references between documents make it easier to navigate between related data.
2. **Improved Query Performance**: Separate collections for portfolio items allow for more efficient queries.
3. **Backward Compatibility**: The changes maintain backward compatibility with existing data.
4. **Cleaner Code**: Helper methods make it easier to work with related documents.
5. **Better Data Integrity**: Proper references ensure data integrity across collections.

## Next Steps

After running the migration scripts, you should:

1. Update your application code to use the new model structure
2. Test the application thoroughly to ensure everything works as expected
3. Consider adding indexes to improve query performance
4. Add validation rules to ensure data integrity 