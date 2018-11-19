﻿// Copyright (c) 2009-2010 Satoshi Nakamoto
// Copyright (c) 2009-2016 The Bitcoin Core developers
// Copyright (c) 2016-2018 The CellLink Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef CELLLINK_PRIMITIVES_BLOCK_H
#define CELLLINK_PRIMITIVES_BLOCK_H

#include "primitives/transaction.h"
#include "io/serialize.h"
#include "coding/uint256.h"

/** Nodes collect new transactions into a block, hash them into a hash tree,
 * and scan through nonce values to make the block's hash satisfy proof-of-work
 * requirements.  When they solve the proof-of-work, they broadcast the block
 * to everyone and the block is added to the block chain.  The first transaction
 * in the block is a special one that creates a new coin owned by the creator
 * of the block.
 */
class CellBlockHeader
{
public:
    // header
    int32_t nVersion;
    uint256 hashPrevBlock;
    uint256 hashMerkleRoot;
    uint256 hashMerkleRootWithData;
    uint256 hashMerkleRootWithPrevData;
    uint32_t nTime;
    uint32_t nBits;
    uint32_t nNonce; // this value in bitcion are added for make different hash, we use to indicate the amount of miner's address

	CellOutPoint prevoutStake;
	CellScript vchBlockSig;

    CellBlockHeader()
    {
        SetNull();
    }

    ADD_SERIALIZE_METHODS;

    template <typename Stream, typename Operation>
    inline void SerializationOp(Stream& s, Operation ser_action) {
        READWRITE(this->nVersion);
        READWRITE(hashPrevBlock);
        READWRITE(hashMerkleRoot);
        READWRITE(hashMerkleRootWithData);
        READWRITE(hashMerkleRootWithPrevData);
        READWRITE(nTime);
        READWRITE(nBits);
        READWRITE(nNonce);

		READWRITE(prevoutStake);
		if (!(s.GetType() & SER_WITHOUT_SIGN))
			READWRITE(vchBlockSig);
    }

    void SetNull()
    {
        nVersion = 0;
        hashPrevBlock.SetNull();
        hashMerkleRoot.SetNull();
        hashMerkleRootWithData.SetNull();
        hashMerkleRootWithPrevData.SetNull();
        nTime = 0;
        nBits = 0;
        nNonce = 0;
		vchBlockSig.clear();
		prevoutStake.SetNull();
    }

    bool IsNull() const
    {
        return (nBits == 0);
    }

    uint256 GetHash() const;
	uint256 GetHashNoSignData() const;
	
    int64_t GetBlockTime() const
    {
        return (int64_t)nTime;
    }
};

class CellBlock : public CellBlockHeader
{
public:
    // network and disk
    std::vector<CellTransactionRef> vtx;
    std::vector<uint16_t> groupSize;
    std::vector<ContractPrevData> prevContractData;

    // memory only
    mutable bool fChecked;

    CellBlock()
    {
        SetNull();
    }

    CellBlock(const CellBlockHeader &header)
    {
        SetNull();
        *((CellBlockHeader*)this) = header;
    }

    ADD_SERIALIZE_METHODS;

    template <typename Stream, typename Operation>
    inline void SerializationOp(Stream& s, Operation ser_action) {
        READWRITE(*(CellBlockHeader*)this);
        READWRITE(vtx);
        READWRITE(groupSize);
        READWRITE(prevContractData);
    }

    void SetNull()
    {
        CellBlockHeader::SetNull();
        vtx.clear();
        groupSize.clear();
        prevContractData.clear();
        fChecked = false;
    }

    CellBlockHeader GetBlockHeader() const
    {
        CellBlockHeader block;
        block.nVersion = nVersion;
        block.hashPrevBlock = hashPrevBlock;
        block.hashMerkleRoot = hashMerkleRoot;
        block.hashMerkleRootWithData = hashMerkleRootWithData;
        block.hashMerkleRootWithPrevData = hashMerkleRootWithPrevData;
        block.nTime = nTime;
        block.nBits = nBits;
        block.nNonce = nNonce;
        return block;
    }
};

/** Describes a place in the block chain to another node such that if the
 * other node doesn't have the same branch, it can find a recent common trunk.
 * The further back it is, the further before the fork it may be.
 */
struct CellBlockLocator
{
    std::vector<uint256> vHave;

    CellBlockLocator() {}

    CellBlockLocator(const std::vector<uint256>& vHaveIn) : vHave(vHaveIn) {}

    ADD_SERIALIZE_METHODS;

    template <typename Stream, typename Operation>
    inline void SerializationOp(Stream& s, Operation ser_action) {
        int nVersion = s.GetVersion();
        if (!(s.GetType() & SER_GETHASH))
            READWRITE(nVersion);
        READWRITE(vHave);
    }

    void SetNull()
    {
        vHave.clear();
    }

    bool IsNull() const
    {
        return vHave.empty();
    }
};

#endif // CELLLINK_PRIMITIVES_BLOCK_H
