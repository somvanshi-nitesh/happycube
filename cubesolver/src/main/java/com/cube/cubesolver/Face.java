package com.cube.cubesolver;

/**
 * Class represents one face of the cube.
 * @author Nitesh
 * 
 */
public class Face {

    private final int id;

    private Piece piece;

    public Face(int id) {
        this.id = id;
    }

    public void setPiece(Piece piece) {
        this.piece = piece;
    }

    public boolean isPieceSet() {
        return piece == null;
    }

    public Piece getPiece() {
        return piece;
    }
}
