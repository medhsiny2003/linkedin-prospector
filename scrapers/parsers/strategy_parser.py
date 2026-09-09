from typing import Dict, List

class StrategyParser:
    @staticmethod
    def determine_strategy(company: str, xray_results: int, has_cookie: bool) -> str:
        if xray_results >= 5:
            return 'xray_only'
        if has_cookie:
            return 'stealth_fallback'
        return 'xray_only'
        
    @staticmethod
    def should_expand_search(results: int, target: int) -> bool:
        return results < target * 0.5
        
    @staticmethod
    def optimize_keywords(keywords: List[str], results_per_keyword: Dict[str, int]) -> List[str]:
        # Sort keywords by result count (descending)
        sorted_keywords = sorted(
            [k for k in keywords if results_per_keyword.get(k, 0) > 0],
            key=lambda k: results_per_keyword.get(k, 0),
            reverse=True
        )
        return sorted_keywords
