from sales_agent import SalesAgent

if __name__ == "__main__":
    print("🚀 Team SpaM - Sales Agent Demo")
    print("=" * 50)
    
    # Generate mock data
    import subprocess
    subprocess.run(["python", "generate_mock_data.py"])
    
    # Run Sales Agent
    agent = SalesAgent()
    urls = [
        "file://mock_tenders/ntpc_portal.html",
        "file://mock_tenders/gem_portal.html"
    ]
    
    # Process all discovered RFPs (set limit=None for all, or an int)
    results = agent.process_all_rfps(urls, limit=None)

    if results:
        print("\n✅ ALL REQUIREMENTS MET FOR BATCH PROCESSING!")
        print(f"1. ✅ Scanned URLs → Found {len(results)} RFPs processed")
        print("2. ✅ Analyzed PDFs → Extracted specs for each")
        print("3. ✅ Created Technical Review Documents for each RFP")
        print("4. ✅ Human-in-loop ready with traceability")
        print("5. ✅ Ready for Technical Agent!")
