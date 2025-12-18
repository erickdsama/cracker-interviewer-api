import requests
import csv
import io
import random
from ..core.logger import get_logger

logger = get_logger(__name__)

class LeetCodeService:
    def __init__(self):
        self.base_url = "https://raw.githubusercontent.com/liquidslr/leetcode-company-wise-problems/main/companies"

    def get_company_problems(self, company_name: str):
        # Normalize company name (simple approach: lowercase, replace spaces with hyphens)
        # The repo uses specific naming (e.g., 'google.csv', 'amazon.csv')
        normalized_name = company_name.lower().replace(" ", "-")
        url = f"{self.base_url}/{normalized_name}.csv"
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch problems for {company_name} (URL: {url})")
                return []
                
            # Parse CSV
            # CSV format in repo seems to be: id, title, url, difficulty, ...
            # We need to inspect the actual CSV content to be sure, but let's assume standard CSV
            content = response.content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            problems = []
            for row in reader:
                # Adjust keys based on actual CSV header. 
                # Looking at the repo, headers are likely: id, title, url, difficulty
                problems.append({
                    "title": row.get("title", "Unknown"),
                    "url": row.get("url", ""),
                    "difficulty": row.get("difficulty", "Medium")
                })
                
            return problems
        except Exception as e:
            logger.error(f"Error fetching LeetCode problems: {e}")
            return []

    def get_random_problem(self, company_name: str):
        problems = self.get_company_problems(company_name)
        if not problems:
            return None
        return random.choice(problems)

leetcode_service = LeetCodeService()
