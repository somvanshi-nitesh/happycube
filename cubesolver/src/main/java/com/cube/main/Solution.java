package com.cube.main;

import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.util.List;

import com.cube.cubesolver.Container;
import com.cube.cubesolver.Cube;
import com.cube.cubesolver.Piece;
import com.cube.cubesolver.Solver;

/**
 * The main class
 * @author Nitesh
 * 
 */
public class Solution {

    public static void main(String[] args) throws IOException {
            FileInputStream fileIn = null;
            try {
                //file = new FileInputStream(args[0]);
            	InputStream is = Solution.class.getClassLoader()
                        .getResourceAsStream("resource/input.txt");
                List<Piece> pieces = Container.getPieces(is);
//                for (Piece piece : pieces) {
//                	System.out.println("P:"+pieces.get(0));
//					System.out.println("P:"+piece);
//				}
                Solver solver = new Solver();
                Cube solution = solver.solve(pieces);
                if (solution != null) {
                    PrintWriter out = new PrintWriter(new FileWriter("src/main/resources/result/result.txt", false), true);
                    solution.print(out);
            		out.close(); 
                    
                } else {
                    System.err.println("No solution found.");
                }
            } finally {
                if (fileIn != null) {
                	fileIn.close();
                }
            }
    }
}
