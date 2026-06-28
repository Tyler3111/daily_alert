import argparse
from modules.config import Config
from modules.orchestrator import Orchestrator

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--workers', type=int, default=4, help='Number of workers')
    parser.add_argument('--config', type=str, default='.env', help='Config file')
    
    args = parser.parse_args()
    
    config = Config(args.config)
    orchestrator = Orchestrator(config)
    
    if args.once:
        await orchestrator.run_once(num_workers=args.workers)
    else:
        await orchestrator.run_continuous()

if __name__ == "__main__":
    asyncio.run(main())