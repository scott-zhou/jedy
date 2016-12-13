
import java.util.List;
import java.util.ArrayList;

public class HappyNum {
    public static boolean isHappy(int n) {
        if(n<=0) return false;
        if(n==1) return true;
        List<Integer> m =new ArrayList<Integer>();
        
        while(true) {
	        int rnum = 0;
	        while(n>=10) {
	            int x = n%10;
	            n = n/10;
	        	rnum += x*x;
	        }
	        rnum += n*n;
	        if(rnum == 1) return true;
	        if(m.contains(rnum)) return false;
	        m.add(rnum);
	        n = rnum;
        }
    }
    
    
	public static void main(String[] args) {
		// TODO Auto-generated method stub
		for (int i=-1; i<1999; i++) {
		System.out.println("Is "+i+" happey? "+(isHappy(i)?"YESSSSSSSSSSSSSSS!!!!!":"no") );
		}
	}

}
