from langchain_core.tools import tool
from typing import List, Dict, Optional
from utils.context_retriever import _hybrid_search, _hybrid_search_with_context


def format_search_results(tool_name: str, results: List[Dict], max_results: int = 5) -> str:
    """Format search results into a readable response"""
    if not results:
        return f"No relevant information found about {tool_name} for your query."
    
    response = f"Here's what I found about {tool_name}:\n\n"
    
    for i, result in enumerate(results[:max_results], 1):
        response += f"{i}. **{result['titre']}**\n"
        
        if result.get('sous-titre1'):
            response += f"   Subtitle: {result['sous-titre1']}\n"
        
        response += f"   Type: {result['type']}\n"
        
        content = result['contenu'][:200]
        if len(result['contenu']) > 200:
            content += "..."
        response += f"   Content: {content}\n"
        
        if result.get('url'):
            response += f"   URL: {result['url']}\n"
        elif result.get('source_url'):
            response += f"   Source: {result['source_url']}\n"
        
        response += "\n"
    
    return response


def perform_hybrid_search(
    query: str, 
    namespace: str, 
    bm25_file: str, 
    index_name: str, 
    top_k: int = 8, 
    alpha: float = 1.0) -> List[Dict]:
    """Perform hybrid search and return formatted results"""
    try:
        results = _hybrid_search(query, namespace, bm25_file, index_name, top_k, alpha)
        
        if not results or not results.get('matches'):
            return []
        
        formatted_results = []
        for match in results['matches']:
            metadata = match.get('metadata', {})
            formatted_results.append({
                "id": match['id'],
                "score": match['score'],
                "titre": metadata.get('titre', ''),
                "sous-titre1": metadata.get('sous-titre1'),
                "sous-titre2": metadata.get('sous-titre2'),
                "contenu": metadata.get('contenu', ''),
                "type": metadata.get('type', ''),
                "url": metadata.get('url'),
                "source_url": metadata.get('source'),
                "resultat": metadata.get('resultat')
            })
        
        return formatted_results
        
    except Exception as e:
        raise Exception(f"Error in search operation: {str(e)}")

@tool
def adsecura(input: str) -> str:
    """
    Provides Adsecura's scenarios or around 'adsecura tool/application/platform', 
    answers general questions about Adsecura, and offers guidance on how to use and configure it.
    """

    try:
        results = perform_hybrid_search(
            input, "Adsecura", "bm25_ads_gen_values.json", "adsecura-gen-hybrid", 8, 1
        )
        return format_search_results("Adsecura", results)
        
    except Exception as e:
        
        return f"Error searching Adsecura information: {str(e)}"


@tool
def dv360(input: str) -> str:
    """
    Use this tool when you need to provide guidance for Google Display Video or DV360.
    """
    try:
        # Primary search
        results = perform_hybrid_search(
            input, "DV360", "bm25_dv_values.json", "dv-360-hybrid", 8, 1
        )
        
        # Add contextual search
        try:
            retriever_context_dv = _hybrid_search_with_context(
                "dv-360-hybrid","dvbm25.json","DV360-Contextual-Hybrid",top_k=150
            )
            contextual_results = retriever_context_dv.invoke(input)
            
            for i, result in enumerate(contextual_results):
                results.append({
                    "id": f"context_{len(results) + i}",
                    "score": 0.8,
                    "titre": result.page_content[:100] + "...",
                    "contenu": result.page_content,
                    "type": "contextual",
                    "sous-titre1": None,
                    "url": None,
                    "source_url": None
                })
        except Exception as e:
            print(f"Warning: Contextual search failed: {e}")
        return format_search_results("DV360", results)
        
    except Exception as e:
        return f"Error searching DV360 information: {str(e)}"

@tool
def sa360(input: str) -> str:
    """
    Use this tool when you need to provide guidance for Google Search Ads 360 or SA360.
    """
    try:
        # First search
        results1 = perform_hybrid_search(
            input, "Searchads", "bm25_sads_values.json", "sads-hybrid", 10, 0.3
        )
        # Second search
        results2 = perform_hybrid_search(
            input, "sadas-cours", "bm25_sads_cours.json", "sads-hybrid", 4, 1
        )
        all_results = results1 + results2
        return format_search_results("SA360", all_results)
        
    except Exception as e:
        return f"Error searching SA360 information: {str(e)}"


@tool
def ga4(input: str) -> str:
    """
    Use this tool when you need to provide guidance for Google Analytics 4 or GA4.
    """
    try:
        results = perform_hybrid_search(
            input, "Analytics", "bm25_ga4_values.json", "ga4-hybrid", 10, 0.4
        )
        return format_search_results("GA4", results)
    except Exception as e:
        return f"Error searching GA4 information: {str(e)}"


@tool
def tagmanager(input: str) -> str:
    """
    Use this tool when you need to provide guidance for Google Tag Manager.
    """
    try:
        results = perform_hybrid_search(
            input, "Tagmanager", "bm25_tag_values.json", "tag-hybrid", 10, 0.1
        )
        return format_search_results("Tag Manager", results)
    except Exception as e:
        return f"Error searching Tag Manager information: {str(e)}"

@tool
def amz(input: str) -> str:
    """
    Provides a full guidance for Amazon DSP support and best practice.
    """
    try:
        results1 = perform_hybrid_search(
            input, "Amazon", "bm25_amz_values.json", "amz-hybrid", 10, 0.2
        )
        results2 = perform_hybrid_search(
            input, "Amazon-study", "bm25_amz_cours.json", "amz-cours-hybrid", 4, 0.5
        )
        all_results = results1 + results2
        return format_search_results("Amazon", all_results)
    except Exception as e:
        return f"Error searching SA360 information: {str(e)}"

@tool
def amc(input: str) -> str:
    """
    Provides a full guidance for Amazon Marketing Cloud support and best practices.
    """
    try:
        results = perform_hybrid_search(
            input, "AMC-context", "bm25_amc_cours.json","amc-hybrid", 12, 0.4
        )
        try:
            retriever_context_dv = _hybrid_search_with_context(
                    "amc-hybrid","dvbm25.json","AMC-Contextual-cours",top_k=150
                )
            contextual_results = retriever_context_dv.invoke(input)
                
            for i, result in enumerate(contextual_results):
                results.append({
                    "id": f"context_{len(results) + i}",
                    "score": 0.8,
                    "titre": result.page_content[:100] + "...",
                    "contenu": result.page_content,
                    "type": "contextual",
                    "sous-titre1": None,
                    "url": None,
                    "source_url": None
                })
        except Exception as e:
            print(f"Warning: Contextual search failed: {e}")
        return format_search_results("AMC", results)
    except Exception as e:
        return f"Error searching AMC information: {str(e)}"

@tool
def amz_api(input: str) -> str:
    """
    Provides a full help for Amazon Ads API(amazon API) and its best practices | guides.
    """
    try:
        results = _hybrid_search_with_context(
            "amz-hybrid","bm25_amz_api.json","amz-ads-api",top_k=50
        )
        return results.invoke(input)
    except Exception as e:
        return f"Error searching Amazon Ads API information: {str(e)}"
    
@tool
def xandr(input: str) -> str:
    """
    Use this tool when you need to provides a guidance for "Xandr | Microsoft Invest" or "Microsoft Learn".
    """
    try:
        result1 = perform_hybrid_search(
            input, "Xandr-Contextual", "bm25_xander.json", "xandr-invest", 8, 0.5
        )
        result2 = perform_hybrid_search(
            input, "Xandr-release", "bm25_xander_release.json", "xandr-invest", 8, 0.7
        )
        all_results = result1 + result2
        return format_search_results("Xandr", all_results)
    except Exception as e:
        print(f"Error searching Xandr information: {str(e)}")
        return f"Error searching Xandr information: {str(e)}"

@tool
def cm360(input: str) -> str:
    """
    Use this tool when you need to provides a guidance for Google Support Compaign Manager or CM360.
    """
    try: 
        results1 = perform_hybrid_search(
            input, "CM360", "bm25_cm_values.json","cm-360-hybrid", 8, 1
        )
        results2 = perform_hybrid_search(
            input, "cm360-cours", "bm25_cm_cours.json","cm-360-hybrid", 8, 0.5
        )
        all_results = results1 + results2
        try:
            result_context = _hybrid_search_with_context(
                "cm-360-hybrid","databm25.json","CM360-Contextual-cours",top_k=150
            )
            contextual_results = result_context.invoke(input)
            for i, result in enumerate(contextual_results):
                all_results.append({
                    "id": f"context_{len(all_results) + i}",
                    "score": 0.8,
                    "titre": result.page_content[:100] + "...",
                    "contenu": result.page_content,
                    "type": "contextual",
                    "sous-titre1": None,
                    "url": None,
                    "source_url": None
                })
            return format_search_results("CM360", all_results)
        except Exception as e:
            print(f"Warning: Contextual search failed: {e}")
    except Exception as e:
        return f"Error searching CM360 information: {str(e)}"
