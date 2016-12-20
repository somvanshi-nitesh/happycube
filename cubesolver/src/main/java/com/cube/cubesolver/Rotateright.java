package com.cube.cubesolver;

/**
 * Class to rotate left an edge.
 * @author Nitesh
 * 
 */
public class Rotateright {

	public String[][] transposeMatrix(String [][] m){
        String[][] temp = new String[m[0].length][m.length];
        for (int i = 0; i < m.length; i++)
            for (int j = 0; j < m[0].length; j++)
                temp[j][i] = m[i][j];
        
        temp = reverse(temp);
        return temp;
    }
	
	
	public  String[][] reverse(String [][] m){
		for(int j = 0; j < m.length; j++){
		    for(int i = 0; i < m[j].length / 2; i++) {
		        String temp = m[j][i];
		        m[j][i] = m[j][m[j].length - i - 1];
		        m[j][m[j].length - i - 1] = temp;
		    }
		}
		return m;
	}
        	
	

	
}
