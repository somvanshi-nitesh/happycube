package com.cube.cubesolver;

/**
 * Class to flip side of a cube.
 * @author Nitesh
 * 
 */
public class Flip {
	public String[][] flip(int width, int height, String[][] abc) {
	    String[][] out = new String[height][width];
	    for (int i = 0; i < height; i++) {
	        for (int j = 0; j < width; j++) {
	            out[i][width - j - 1] = abc[i][j];
	        }
	    }
	    return out;
	}
}
