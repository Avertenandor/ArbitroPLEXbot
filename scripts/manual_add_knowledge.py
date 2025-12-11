import asyncio
import sys
from pathlib import Path


# Add project root to python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.services.knowledge_base import get_knowledge_base


async def main():
    print("Initializing Knowledge Base...")
    kb = get_knowledge_base()

    entries_to_add = [
        {
            "question": "Как работает модель NFT кроликов?",
            "answer": "Инвестор покупает NFT и получает долю в реальном кролике. Кролик размножается, и инвестор получает доход от продажи потомства на племя.",
            "category": "NFT Кролики",
            "clarification": "Это долгосрочный актив - кролики не забиваются, а 'работают' годами. Прозрачность через бота + (в будущем) трансляции.",
        },
        {
            "question": "В чем уникальность модели NFT кроликов?",
            "answer": "Это действительно революционная модель! Первый в мире 'живой DeFi' где NFT = реальное животное, приносящее реальный доход.",
            "category": "NFT Кролики",
            "clarification": "Живой DeFi актив.",
        },
    ]

    print(f"Adding {len(entries_to_add)} entries...")

    for item in entries_to_add:
        # Check if already exists to avoid duplicates
        existing = kb.search(item["question"])
        if existing:
            print(f"Skipping existing: {item['question']}")
            continue

        kb.add_learned_entry(
            question=item["question"],
            answer=item["answer"],
            category=item["category"],
            source_user="VladarevInvestBrok",  # Assuming this is the admin
            needs_verification=False,  # Auto-verify since I am adding it manually per instruction
        )
        # Update clarification manually since add_learned_entry sets a default one
        last_entry = kb.entries[-1]
        last_entry["clarification"] = item["clarification"]
        kb.save()
        print(f"Added: {item['question']}")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
